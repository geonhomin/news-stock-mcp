# server.py
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY")

app = Server("news-stock-mcp")

NEWS_BASE_URL = "https://newsapi.org/v2"
AV_BASE_URL = "https://www.alphavantage.co/query"


# ─────────────────────────────────────────
# 공통 함수
# ─────────────────────────────────────────

async def fetch_news(endpoint: str, params: dict) -> dict:
    """NewsAPI GET 요청"""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{NEWS_BASE_URL}/{endpoint}",
            params={**params, "apiKey": NEWS_API_KEY}
            # **params: 딕셔너리 언패킹 — params 내용을 펼쳐서 합침
            # apiKey는 모든 요청에 필수라 여기서 자동으로 추가
        )
        response.raise_for_status()
        return response.json()


async def fetch_stock(params: dict) -> dict:
    """Alpha Vantage GET 요청"""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            AV_BASE_URL,
            params={**params, "apikey": ALPHA_VANTAGE_KEY}
        )
        response.raise_for_status()
        return response.json()


def format_article(article: dict) -> str:
    """뉴스 기사 하나를 텍스트로 포맷팅"""
    title = article.get("title", "제목 없음")
    source = article.get("source", {}).get("name", "출처 없음")
    published = article.get("publishedAt", "")[:10]  # 날짜만 추출
    description = article.get("description") or "설명 없음"
    url = article.get("url", "")

    return f"""📰 {title}
출처: {source} | 날짜: {published}
{description[:200]}{"..." if len(description) > 200 else ""}
URL: {url}""".strip()


# ─────────────────────────────────────────
# Tools
# ─────────────────────────────────────────

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="search_news",
            description="키워드로 최신 뉴스를 검색합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "검색 키워드 (예: AI, 삼성, bitcoin)"
                    },
                    "language": {
                        "type": "string",
                        "description": "언어 코드 (ko: 한국어, en: 영어)",
                        "default": "ko"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "반환할 기사 수 (기본값: 5)",
                        "default": 5
                    }
                },
                "required": ["keyword"]
            }
        ),
        types.Tool(
            name="get_top_headlines",
            description="국가별 실시간 헤드라인 뉴스를 가져옵니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "country": {
                        "type": "string",
                        "description": "국가 코드 (kr: 한국, us: 미국, jp: 일본)",
                        "default": "kr"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "반환할 기사 수 (기본값: 5)",
                        "default": 5
                    }
                }
            }
        ),
        types.Tool(
            name="get_stock_price",
            description="주식 현재가 및 당일 시가/고가/저가/거래량을 조회합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "티커 심볼 (예: AAPL, TSLA, 005930.KS)"
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="get_stock_daily",
            description="주식의 최근 N일 일별 시가/종가/거래량 데이터를 조회합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "티커 심볼 (예: AAPL, TSLA)"
                    },
                    "days": {
                        "type": "integer",
                        "description": "조회할 일수 (기본값: 5)",
                        "default": 5
                    }
                },
                "required": ["symbol"]
            }
        ),
        types.Tool(
            name="search_symbol",
            description="회사명으로 주식 티커 심볼을 검색합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "company": {
                        "type": "string",
                        "description": "회사명 (예: Apple, Tesla, Samsung)"
                    }
                },
                "required": ["company"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        # ── 뉴스 ──────────────────────────────
        if name == "search_news":
            limit = min(arguments.get("limit", 5), 10)
            data = await fetch_news("everything", {
                "q": arguments["keyword"],
                "language": arguments.get("language", "ko"),
                "pageSize": limit,
                "sortBy": "publishedAt"  # 최신순 정렬
            })
            articles = data.get("articles", [])
            if not articles:
                return [types.TextContent(type="text", text="검색 결과가 없습니다.")]

            total = data.get("totalResults", 0)
            results = "\n\n".join([format_article(a) for a in articles])
            return [types.TextContent(type="text", text=f"총 {total}건 중 {len(articles)}개 표시\n\n{results}")]

        elif name == "get_top_headlines":
            limit = min(arguments.get("limit", 5), 10)
            data = await fetch_news("top-headlines", {
                "country": arguments.get("country", "kr"),
                "pageSize": limit
            })
            articles = data.get("articles", [])
            if not articles:
                return [types.TextContent(type="text", text="헤드라인 뉴스를 가져올 수 없습니다.")]

            results = "\n\n".join([format_article(a) for a in articles])
            return [types.TextContent(type="text", text=f"헤드라인 {len(articles)}건\n\n{results}")]

        # ── 주식 ──────────────────────────────
        elif name == "get_stock_price":
            symbol = arguments["symbol"].upper()
            data = await fetch_stock({
                "function": "GLOBAL_QUOTE",
                "symbol": symbol
            })

            quote = data.get("Global Quote", {})
            if not quote:
                return [types.TextContent(type="text", text=f"{symbol} 데이터를 찾을 수 없습니다.")]

            # 각 필드 추출 (Alpha Vantage는 키 앞에 숫자가 붙어있어)
            price = quote.get("05. price", "N/A")
            open_ = quote.get("02. open", "N/A")
            high = quote.get("03. high", "N/A")
            low = quote.get("04. low", "N/A")
            volume = quote.get("06. volume", "N/A")
            change = quote.get("09. change", "N/A")
            change_pct = quote.get("10. change percent", "N/A")
            latest_day = quote.get("07. latest trading day", "N/A")

            result = f"""📈 {symbol} 주가 정보 ({latest_day})
현재가: ${price}
변동: {change} ({change_pct})
시가: ${open_} | 고가: ${high} | 저가: ${low}
거래량: {int(float(volume)):,}"""

            return [types.TextContent(type="text", text=result)]

        elif name == "get_stock_daily":
            symbol = arguments["symbol"].upper()
            days = min(arguments.get("days", 5), 30)
            data = await fetch_stock({
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": "compact"  # 최근 100일치
            })

            time_series = data.get("Time Series (Daily)", {})
            if not time_series:
                return [types.TextContent(type="text", text=f"{symbol} 데이터를 찾을 수 없습니다.")]

            # 날짜 기준 내림차순 정렬 후 N일치만 추출
            # sorted()의 reverse=True: 최신 날짜가 앞으로
            dates = sorted(time_series.keys(), reverse=True)[:days]

            lines = [f"📊 {symbol} 최근 {days}일 주가"]
            for date in dates:
                d = time_series[date]
                close = d.get("4. close", "N/A")
                open_ = d.get("1. open", "N/A")
                volume = d.get("5. volume", "N/A")
                lines.append(f"{date} | 종가: ${close} | 시가: ${open_} | 거래량: {int(float(volume)):,}")

            return [types.TextContent(type="text", text="\n".join(lines))]

        elif name == "search_symbol":
            data = await fetch_stock({
                "function": "SYMBOL_SEARCH",
                "keywords": arguments["company"]
            })

            matches = data.get("bestMatches", [])
            if not matches:
                return [types.TextContent(type="text", text="검색 결과가 없습니다.")]

            lines = [f"🔍 '{arguments['company']}' 검색 결과"]
            for m in matches[:5]:  # 상위 5개만
                symbol = m.get("1. symbol", "")
                name = m.get("2. name", "")
                region = m.get("4. region", "")
                currency = m.get("8. currency", "")
                lines.append(f"{symbol} | {name} | {region} | {currency}")

            return [types.TextContent(type="text", text="\n".join(lines))]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except httpx.HTTPStatusError as e:
        return [types.TextContent(type="text", text=f"API 에러: {e.response.status_code}")]
    except httpx.TimeoutException:
        return [types.TextContent(type="text", text="API 응답 시간 초과. 잠시 후 다시 시도해주세요.")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"에러 발생: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
