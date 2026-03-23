# News & Stock MCP Server

NewsAPI와 Alpha Vantage API를 연동한 MCP 서버입니다.
Claude Desktop에서 실시간 뉴스와 주식 정보를 자연어로 조회할 수 있습니다.

## Tools

| Tool | 설명 |
|---|---|
| `search_news` | 키워드로 최신 뉴스 검색 |
| `get_top_headlines` | 국가별 헤드라인 뉴스 |
| `get_stock_price` | 주식 현재가 조회 |
| `get_stock_daily` | 일별 주가 차트 데이터 |
| `search_symbol` | 회사명으로 티커 심볼 검색 |

## 설치
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install mcp httpx python-dotenv
```

## 설정

`.env` 파일 생성:
```
NEWS_API_KEY=your_newsapi_key
ALPHA_VANTAGE_KEY=your_alphavantage_key
```

- NewsAPI 발급: https://newsapi.org/register
- Alpha Vantage 발급: https://www.alphavantage.co/support/#api-key

## Claude Desktop 연결

`claude_desktop_config.json`에 추가:
```json
{
  "mcpServers": {
    "news-stock-mcp": {
      "command": "/path/to/.venv/bin/python3",
      "args": ["/path/to/server.py"]
    }
  }
}
```
