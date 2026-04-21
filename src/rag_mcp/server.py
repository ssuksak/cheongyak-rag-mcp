"""청약(주택청약) RAG MCP Server."""

import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .config import get_config
from .data_api import DataGoKrClient
from .indexer import SUBSCRIPTION_GUIDE, index_subscriptions
from .parser import parse_document, PARSERS
from .chunker import chunk_document
from .rag import ask_question
from .scraper import CheongyakScraper
from .vectorstore import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "cheongyak-rag",
    instructions="""한국 주택청약 정보 RAG 서버입니다.

주요 기능:
1. 현재 청약가능 주택 목록 조회 (청약홈 실시간)
2. 청약 일정 캘린더 조회
3. 청약 자격 요건 안내
4. 키워드로 청약 검색
5. PDF/HWP 공고문 RAG 색인 및 Q&A
6. 공공데이터포털 API 연동 (API 키 필요)

사용 예시:
- "오늘자 청약리스트 보여줘" → fetch_current_subscriptions
- "서울 청약 뭐 있어?" → fetch_current_subscriptions(region="서울")
- "청약 자격 알려줘" → get_subscription_guide
- "OO아파트 정보 알려줘" → search_subscriptions(keyword="OO")
- "이 PDF 공고문 분석해줘" → ingest_file 후 ask_about_documents""",
)

_vector_store: VectorStore | None = None
_scraper: CheongyakScraper | None = None


def _get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def _get_scraper() -> CheongyakScraper:
    global _scraper
    if _scraper is None:
        _scraper = CheongyakScraper()
    return _scraper


# ─── 청약홈 실시간 조회 Tools ─────────────────────────────────────


@mcp.tool()
def fetch_current_subscriptions(region: str | None = None, page: int = 1) -> str:
    """청약홈에서 현재 청약가능한 주택 목록을 실시간 조회합니다.

    Args:
        region: 지역 필터 (예: '서울', '경기', '부산'). 미지정 시 전국.
        page: 페이지 번호 (기본 1)
    """
    scraper = _get_scraper()
    items = scraper.fetch_current_subscriptions(region=region, page=page)

    if not items:
        return json.dumps(
            {"message": "현재 청약가능한 주택이 없습니다.", "region": region},
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "total": len(items),
            "region": region or "전국",
            "subscriptions": [asdict(item) for item in items],
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def fetch_remaining_subscriptions(region: str | None = None) -> str:
    """잔여세대 청약공고 목록을 조회합니다.

    Args:
        region: 지역 필터 (예: '서울', '경기')
    """
    scraper = _get_scraper()
    items = scraper.fetch_remaining_subscriptions(region=region)

    if not items:
        return json.dumps(
            {"message": "잔여세대 청약공고가 없습니다.", "region": region},
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "total": len(items),
            "region": region or "전국",
            "subscriptions": [asdict(item) for item in items],
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def search_subscriptions(keyword: str) -> str:
    """키워드로 청약 주택을 검색합니다 (주택명, 지역, 시공사).

    Args:
        keyword: 검색 키워드 (예: '자이', '서울', '롯데')
    """
    scraper = _get_scraper()
    items = scraper.search_subscriptions(keyword)

    if not items:
        return json.dumps(
            {"message": f"'{keyword}' 검색 결과가 없습니다.", "keyword": keyword},
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "keyword": keyword,
            "total": len(items),
            "results": [asdict(item) for item in items],
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def fetch_subscription_detail(name: str) -> str:
    """특정 청약 주택의 상세 정보를 조회합니다.

    Args:
        name: 주택명 (예: '공덕역자이르네')
    """
    scraper = _get_scraper()
    detail = scraper.fetch_subscription_detail(name)

    if not detail:
        return json.dumps(
            {"message": f"'{name}' 상세 정보를 찾을 수 없습니다."},
            ensure_ascii=False,
        )

    return json.dumps(asdict(detail), ensure_ascii=False, indent=2)


@mcp.tool()
def download_and_ingest_notice(name: str) -> str:
    """청약홈에서 특정 주택의 모집공고문(붙임파일)을 다운로드하고 자동 색인합니다.

    Args:
        name: 주택명 (예: '공덕역자이르네')
    """
    scraper = _get_scraper()
    config = get_config()
    saved_files = scraper.download_attachment(name, save_dir=config.documents_dir)

    if not saved_files:
        return json.dumps(
            {"message": f"'{name}'의 다운로드 가능한 공고문이 없습니다."},
            ensure_ascii=False,
        )

    vs = _get_vector_store()
    results = {"downloaded": [], "ingested": [], "failed": []}

    for filepath in saved_files:
        try:
            parsed = parse_document(filepath)
            chunks = chunk_document(parsed)
            if chunks:
                added = vs.add_chunks(chunks)
                results["ingested"].append({"file": filepath, "chunks": added})
            else:
                results["downloaded"].append(
                    {"file": filepath, "note": "텍스트 추출 불가"}
                )
        except Exception as e:
            results["failed"].append({"file": filepath, "error": str(e)})

    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def fetch_subscription_calendar(
    year: int | None = None, month: int | None = None
) -> str:
    """청약 일정 캘린더를 조회합니다.

    Args:
        year: 연도 (기본: 현재 연도)
        month: 월 (기본: 현재 월)
    """
    scraper = _get_scraper()
    entries = scraper.fetch_calendar(year=year, month=month)

    if not entries:
        return json.dumps(
            {
                "message": "해당 기간의 청약 일정이 없습니다.",
                "year": year,
                "month": month,
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "year": year,
            "month": month,
            "total": len(entries),
            "entries": [asdict(e) for e in entries],
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def get_subscription_guide() -> str:
    """청약 자격 요건, 순위, 특별공급 등 청약 관련 종합 가이드를 제공합니다."""
    return SUBSCRIPTION_GUIDE


# ─── RAG 색인 및 검색 Tools ────────────────────────────────────────


@mcp.tool()
def index_cheongyak_data(region: str | None = None) -> str:
    """청약홈 실시간 데이터를 ChromaDB에 색인하여 RAG 검색이 가능하게 합니다.

    Args:
        region: 지역 필터 (미지정 시 전국)
    """
    vs = _get_vector_store()
    result = index_subscriptions(vs, region=region)
    return json.dumps(
        {
            "status": "success",
            "indexed": result["indexed"],
            "total_items": result["total_items"],
        },
        ensure_ascii=False,
    )


@mcp.tool()
def search_cheongyak_rag(query: str, top_k: int = 5) -> str:
    """색인된 청약 데이터에서 의미론적 검색을 수행합니다.

    Args:
        query: 검색 질의 (예: '서울 분양주택', '신혼부부 특별공급')
        top_k: 반환할 결과 수
    """
    vs = _get_vector_store()
    results = vs.search(query, top_k=top_k)

    if not results:
        return json.dumps(
            {
                "message": "검색 결과가 없습니다. 먼저 index_cheongyak_data를 실행하세요.",
                "query": query,
            },
            ensure_ascii=False,
        )

    output = []
    for i, r in enumerate(results, 1):
        meta = r["metadata"]
        output.append(
            {
                "rank": i,
                "relevance": r["relevance_score"],
                "name": meta.get("name", ""),
                "region": meta.get("region", ""),
                "period": meta.get("subscription_period", ""),
                "text_preview": r["text"][:400],
            }
        )

    return json.dumps(
        {"query": query, "total_results": len(results), "results": output},
        ensure_ascii=False,
        indent=2,
    )


# ─── PDF/HWP 공고문 Tools ──────────────────────────────────────────


@mcp.tool()
def ingest_documents(directory: str | None = None) -> str:
    """PDF/HWP 공고문을 디렉터리에서 찾아 색인합니다.

    Args:
        directory: 문서 디렉터리 경로 (기본: 설정된 DOCUMENTS_DIR)
    """
    config = get_config()
    target_dir = directory or config.documents_dir
    dir_path = Path(target_dir)

    if not dir_path.exists():
        return json.dumps(
            {"error": f"디렉터리가 존재하지 않습니다: {target_dir}"}, ensure_ascii=False
        )

    files = []
    for ext in PARSERS:
        files.extend(dir_path.rglob(f"*{ext}"))

    if not files:
        return json.dumps(
            {"error": f"지원되는 문서가 없습니다: {target_dir}"}, ensure_ascii=False
        )

    vs = _get_vector_store()
    results = {"total_files": len(files), "processed": 0, "failed": 0, "details": []}

    for filepath in sorted(files):
        try:
            parsed = parse_document(str(filepath))
            chunks = chunk_document(parsed)
            if chunks:
                added = vs.add_chunks(chunks)
                results["processed"] += 1
                results["details"].append(
                    {"filename": parsed.filename, "status": "success", "chunks": added}
                )
            else:
                results["details"].append(
                    {"filename": parsed.filename, "status": "skipped"}
                )
        except Exception as e:
            results["failed"] += 1
            results["details"].append(
                {"filename": filepath.name, "status": "error", "error": str(e)}
            )

    return json.dumps(results, ensure_ascii=False, indent=2)


@mcp.tool()
def ingest_file(filepath: str) -> str:
    """단일 PDF/HWP 공고문 파일을 색인합니다.

    Args:
        filepath: 파일 경로
    """
    file_path = Path(filepath)
    if not file_path.exists():
        return json.dumps({"error": f"파일이 없습니다: {filepath}"}, ensure_ascii=False)

    try:
        parsed = parse_document(str(file_path))
        chunks = chunk_document(parsed)
        if chunks:
            vs = _get_vector_store()
            added = vs.add_chunks(chunks)
            return json.dumps(
                {"filename": parsed.filename, "status": "success", "chunks": added},
                ensure_ascii=False,
            )
        return json.dumps(
            {"filename": parsed.filename, "status": "skipped"}, ensure_ascii=False
        )
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


@mcp.tool()
def ask_about_documents(query: str, top_k: int = 5) -> str:
    """색인된 문서를 바탕으로 질문에 답변합니다 (RAG).

    Args:
        query: 질문 내용
        top_k: 검색할 문서 수
    """
    vs = _get_vector_store()
    result = ask_question(query, vs, top_k=top_k)
    return json.dumps(result, ensure_ascii=False, indent=2)


# ─── 공공데이터포털 API Tools ──────────────────────────────────────


@mcp.tool()
def fetch_apt_list_api(region_code: str | None = None, page: int = 1) -> str:
    """공공데이터포털 API로 APT 분양정보를 조회합니다. (DATA_GO_KR_API_KEY 필요)

    Args:
        region_code: 법정동코드 (예: '11110' - 서울 종로구)
        page: 페이지 번호
    """
    client = DataGoKrClient()
    result = client.fetch_apt_list(region_code=region_code, page=page)
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def list_documents() -> str:
    """현재 색인된 모든 문서 목록을 반환합니다."""
    vs = _get_vector_store()
    docs = vs.list_documents()
    return json.dumps(
        {"total": len(docs), "documents": docs}, ensure_ascii=False, indent=2
    )


@mcp.tool()
def get_stats() -> str:
    """색인 통계를 반환합니다."""
    vs = _get_vector_store()
    stats = vs.get_stats()
    return json.dumps(stats, ensure_ascii=False, indent=2)


def main():
    config = get_config()
    logger.info("Starting 청약 RAG MCP Server")
    logger.info(f"  Documents dir: {config.documents_dir}")
    logger.info(f"  ChromaDB dir:  {config.chroma_persist_dir}")
    logger.info(f"  Embedding:     {config.embedding_model}")
    mcp.run()


if __name__ == "__main__":
    main()
