# Cheongyak RAG MCP

한국 주택청약 정보 RAG MCP 서버. 청약홈(applyhome.co.kr) 실시간 데이터 + PDF/HWP 공고문 RAG 검색.

## Features

- **실시간 청약 조회** — 청약홈에서 현재 청약가능 주택 목록, 상세정보, 분양가, 공급세대
- **붙임파일 자동 처리** — 모집공고문 PDF 자동 다운로드 + ChromaDB 색인
- **RAG Q&A** — 색인된 공고문 기반 질의응답 (OpenAI 연동)
- **청약 가이드** — 자격요건, 순위, 특별공급 안내
- **PDF/HWP 지원** — 청약공고, 붙임자료 파일 직접 색인
- **공공데이터포털** — data.go.kr API 연동 (선택)

## Quick Start

### Install

```bash
pip install cheongyak-rag-mcp
```

### Configure

Create `.env` file:

```env
# Optional: OpenAI API key for RAG Q&A
OPENAI_API_KEY=sk-your-key

# Optional: data.go.kr API key for public data
DATA_GO_KR_API_KEY=your-key
```

### OpenCode

Add to `~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "cheongyak": {
      "type": "local",
      "command": ["cheongyak-mcp"],
      "enabled": true
    }
  }
}
```

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cheongyak": {
      "command": "cheongyak-mcp"
    }
  }
}
```

### Cursor / Other MCP Clients

```json
{
  "mcpServers": {
    "cheongyak": {
      "command": "cheongyak-mcp",
      "cwd": "/path/to/project"
    }
  }
}
```

## MCP Tools

### Real-time Subscription Data

| Tool | Description |
|---|---|
| `fetch_current_subscriptions` | 현재 청약가능 주택 목록 (청약홈 실시간) |
| `fetch_remaining_subscriptions` | 잔여세대 청약공고 |
| `search_subscriptions` | 키워드 검색 (주택명/지역/시공사) |
| `fetch_subscription_detail` | 상세정보 (공급세대/분양가/일정/특별공급) |
| `fetch_subscription_calendar` | 청약 일정 캘린더 |
| `download_and_ingest_notice` | 모집공고문 PDF 자동 다운로드 + 색인 |
| `get_subscription_guide` | 청약 자격/순위/특별공급 가이드 |

### RAG Search

| Tool | Description |
|---|---|
| `index_cheongyak_data` | 실시간 데이터 ChromaDB 색인 |
| `search_cheongyak_rag` | 의미론적 검색 |
| `ingest_documents` | PDF/HWP 파일 일괄 색인 |
| `ingest_file` | 단일 파일 색인 |
| `ask_about_documents` | 문서 기반 Q&A |

### Public Data API

| Tool | Description |
|---|---|
| `fetch_apt_list_api` | 공공데이터포털 APT 분양정보 (API 키 필요) |
| `list_documents` | 색인된 문서 목록 |
| `get_stats` | 통계 정보 |

## Usage Examples

```
"오늘자 청약리스트 보여줘"           → fetch_current_subscriptions
"서울 청약 뭐 있어?"                 → search_subscriptions(keyword="서울")
"공덕역자이르네 상세정보"             → fetch_subscription_detail(name="공덕역자이르네")
"공고문 다운받아서 분석해줘"          → download_and_ingest_notice(name="...")
"청약 1순위 조건이 뭐야?"            → get_subscription_guide
"이 PDF 공고문에서 분양가 알려줘"     → ingest_file → ask_about_documents
```

## Architecture

```
청약홈 (applyhome.co.kr) ──scraper──→ 실시간 데이터
                                        ↓
PDF/HWP 공고문 ──parser──→ 청킹 ──→ 임베딩 ──→ ChromaDB
                                              ↓
                              MCP Tools ←── 검색/조회
                                  ↓
                          LLM (OpenCode, Claude, etc.)
```

## Tech Stack

- **Python 3.10+**
- **MCP SDK** — Model Context Protocol server
- **ChromaDB** — Vector store (persistent, local)
- **Sentence Transformers** — Korean embedding (`jhgan/ko-sroberta-multitask`)
- **PyMuPDF** — PDF parsing
- **BeautifulSoup** — 청약홈 web scraping
- **OpenAI** — RAG Q&A (optional)

## Configuration

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | OpenAI API key (RAG Q&A용, 선택) |
| `DATA_GO_KR_API_KEY` | — | 공공데이터포털 API 키 (선택) |
| `EMBEDDING_MODEL` | `jhgan/ko-sroberta-multitask` | 임베딩 모델 |
| `CHROMA_PERSIST_DIR` | `./data/chroma_db` | ChromaDB 경로 |
| `DOCUMENTS_DIR` | `./data/documents` | 문서 경로 |
| `CACHE_TTL_MINUTES` | `30` | 캐시 TTL (분) |

## Development

```bash
git clone https://github.com/your-username/cheongyak-rag-mcp.git
cd cheongyak-rag-mcp
pip install -e ".[dev]"
python -m pytest
```

## License

MIT
