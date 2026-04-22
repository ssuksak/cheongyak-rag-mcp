# 🏠 Cheongyak RAG MCP

한국 주택청약 정보 RAG MCP 서버. 청약홈(applyhome.co.kr) 실시간 데이터 + PDF/HWP 공고문 RAG 검색.

**[English](#english) below**

## 특징

- **실시간 청약 조회** — 청약홈에서 현재 청약가능 주택 목록, 상세정보, 분양가, 공급세대
- **붙임파일 자동 처리** — 모집공고문 PDF 자동 다운로드 + ChromaDB 색인
- **RAG Q&A** — 색인된 공고문 기반 질의읜 (OpenAI 연동, 선택)
- **청약 가이드** — 자격요건, 순위, 특별공급 안내
- **PDF/HWP 지원** — 청약공고, 붙임자료 파일 직접 색인
- **공공데이터포털** — data.go.kr API 연동 (선택)
- **API 키 불필요** — 기본적으로 청약홈 스크래핑으로 작동

## 설치

### pip (Python)

```bash
pip install cheongyak-rag-mcp
```

### npm (Node.js 래퍼)

```bash
npx cheongyak-rag-mcp
```

> npm으로 실행하면 자동으로 Python 패키지를 설치합니다.

### 소스에서 설치

```bash
git clone https://github.com/ssuksak/cheongyak-rag-mcp.git
cd cheongyak-rag-mcp
pip install -e .
```

## 설정

### 자동 설정 (권장)

최초 실행 시 인터랙티브 설정 마법사가 실행됩니다:

```bash
cheongyak-mcp config
```

### 수동 설정

`~/.config/cheongyak-mcp/.env` 파일 생성:

```env
# 선택: OpenAI API 키 (RAG Q&A용)
OPENAI_API_KEY=sk-your-key

# 선택: 공공데이터포털 API 키
DATA_GO_KR_API_KEY=your-key
```

> API 키 없이도 청약홈 스크래핑으로 모든 기능 사용 가능합니다.

## MCP 클라이언트 설정

### OpenCode

`~/.config/opencode/opencode.json`:

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

`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cheongyak": {
      "command": "cheongyak-mcp"
    }
  }
}
```

### Cursor / 기타 MCP 클라이언트

```json
{
  "mcpServers": {
    "cheongyak": {
      "command": "cheongyak-mcp",
      "args": []
    }
  }
}
```

## MCP 도구 목록

### 실시간 청약 데이터

| 도구 | 설명 |
|---|---|
| `fetch_current_subscriptions` | 현재 청약가능 주택 목록 (청약홈 실시간) |
| `fetch_remaining_subscriptions` | 잔여세대 청약공고 |
| `search_subscriptions` | 키워드 검색 (주택명/지역/시공사) |
| `fetch_subscription_detail` | 상세정보 (공급세대/분양가/일정/특별공급) |
| `fetch_subscription_calendar` | 청약 일정 캘린더 |
| `download_and_ingest_notice` | 모집공고문 PDF 자동 다운로드 + 색인 |
| `get_subscription_guide` | 청약 자격/순위/특별공급 가이드 |

### RAG 검색

| 도구 | 설명 |
|---|---|
| `index_cheongyak_data` | 실시간 데이터 ChromaDB 색인 |
| `search_cheongyak_rag` | 의미론적 검색 |
| `ingest_documents` | PDF/HWP 파일 일괄 색인 |
| `ingest_file` | 단일 파일 색인 |
| `ask_about_documents` | 문서 기반 Q&A |

### 공공데이터포털 API

| 도구 | 설명 |
|---|---|
| `fetch_apt_list_api` | 공공데이터포털 APT 분양정보 (API 키 필요) |
| `list_documents` | 색인된 문서 목록 |
| `get_stats` | 통계 정보 |

## 사용 예시

```
"오늘자 청약리스트 보여줘"           → fetch_current_subscriptions
"서울 청약 뭐 있어?"                 → search_subscriptions(keyword="서울")
"공덕역자이르네 상세정보"             → fetch_subscription_detail
"공고문 다운받아서 분석해줘"          → download_and_ingest_notice
"청약 1순위 조건이 뭐야?"            → get_subscription_guide
"이 PDF 공고문에서 분양가 알려줘"     → ingest_file → ask_about_documents
```

## 아키텍처

```
청약홈 (applyhome.co.kr) ──scraper──→ 실시간 데이터
                                        ↓
PDF/HWP 공고문 ──parser──→ 청킹 ──→ 임베딩 ──→ ChromaDB
                                              ↓
                              MCP Tools ←── 검색/조회
                                  ↓
                          LLM (OpenCode, Claude, etc.)
```

## 기술 스택

- **Python 3.10+**
- **MCP SDK** — Model Context Protocol server
- **ChromaDB** — Vector store (persistent, local)
- **Sentence Transformers** — Korean embedding (`jhgan/ko-sroberta-multitask`)
- **PyMuPDF** — PDF parsing
- **BeautifulSoup** — 청약홈 web scraping
- **OpenAI** — RAG Q&A (optional)

## 환경 변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `OPENAI_API_KEY` | — | OpenAI API 키 (RAG Q&A용, 선택) |
| `DATA_GO_KR_API_KEY` | — | 공공데이터포털 API 키 (선택) |
| `EMBEDDING_MODEL` | `jhgan/ko-sroberta-multitask` | 임베딩 모델 |
| `CHROMA_PERSIST_DIR` | `~/.config/cheongyak-mcp/chroma_db` | ChromaDB 경로 |
| `DOCUMENTS_DIR` | `~/.config/cheongyak-mcp/documents` | 문서 경로 |
| `CACHE_TTL_MINUTES` | `30` | 캐시 TTL (분) |

## 개발

```bash
git clone https://github.com/ssuksak/cheongyak-rag-mcp.git
cd cheongyak-rag-mcp
pip install -e ".[dev]"
python -m pytest
```

## 라이선스

MIT

---

<a id="english"></a>

## English

A Korean housing subscription (청약) RAG MCP server. Provides real-time subscription data from 청약홈 (applyhome.co.kr) and RAG-powered Q&A over housing notice PDFs.

### Features

- **Real-time subscription data** — Fetch current housing subscriptions from 청약홈
- **Automatic PDF processing** — Download and index housing notice PDFs with ChromaDB
- **RAG Q&A** — Ask questions about indexed documents (OpenAI integration, optional)
- **Subscription guide** — Qualification requirements, priority rules, special supply info
- **PDF/HWP support** — Direct file indexing for housing notices and attachments
- **Public data API** — data.go.kr integration (optional)
- **No API key required** — Works out of the box via web scraping

### Install

```bash
# Python
pip install cheongyak-rag-mcp

# Node.js
npx cheongyak-rag-mcp
```

### Quick Start

1. Install and run with your MCP client (Claude Desktop, OpenCode, Cursor, etc.)
2. Ask questions in Korean about housing subscriptions
3. Optionally configure API keys for enhanced features

### License

MIT
