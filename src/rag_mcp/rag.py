"""RAG Q&A module using retrieved context and LLM."""

import logging

from openai import OpenAI

from .config import get_config
from .vectorstore import VectorStore

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """당신은 한국어 공공공고 및 청약공고 문서 전문 분석가입니다.

주어진 참고 문서를 바탕으로 사용자의 질문에 정확하게 답변하세요.

규칙:
1. 참고 문서에서 찾을 수 있는 정보만 사용하여 답변하세요.
2. 참고 문서에 해당 정보가 없으면 "제공된 문서에서 해당 정보를 찾을 수 없습니다."라고 명시하세요.
3. 답변 시 출처(문서명, 페이지)를 함께 표시하세요.
4. 전문 용어는 쉽게 설명해주세요.
5. 한국어로 답변하세요."""


def ask_question(
    query: str, vector_store: VectorStore, top_k: int | None = None
) -> dict:
    config = get_config()

    search_results = vector_store.search(query, top_k=top_k)

    if not search_results:
        return {
            "answer": "검색 결과가 없습니다. 먼저 문서를 색인해주세요.",
            "sources": [],
            "total_chunks_searched": 0,
        }

    context_parts = []
    sources = []

    for i, result in enumerate(search_results, 1):
        meta = result["metadata"]
        source_info = f"문서: {meta.get('filename', '알 수 없음')}, 페이지: {meta.get('page_number', '?')}"
        context_parts.append(f"[참고자료 {i}] ({source_info})\n{result['text']}")
        if source_info not in sources:
            sources.append(source_info)

    context = "\n\n".join(context_parts)

    user_prompt = f"""다음 참고 문서를 바탕으로 질문에 답변해주세요.

# 참고 문서
{context}

# 질문
{query}

답변:"""

    if not config.openai_api_key or config.openai_api_key == "sk-your-api-key-here":
        return {
            "answer": _build_context_only_answer(query, search_results),
            "sources": sources,
            "total_chunks_searched": len(search_results),
        }

    try:
        client = OpenAI(api_key=config.openai_api_key, base_url=config.llm_base_url)
        response = client.chat.completions.create(
            model=config.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=2000,
        )
        answer = response.choices[0].message.content
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        answer = _build_context_only_answer(query, search_results)

    return {
        "answer": answer,
        "sources": sources,
        "total_chunks_searched": len(search_results),
    }


def _build_context_only_answer(query: str, search_results: list[dict]) -> str:
    parts = [f"질문: {query}\n\n검색된 관련 문서 내용:\n"]

    for i, result in enumerate(search_results, 1):
        meta = result["metadata"]
        score = result.get("relevance_score", 0)
        parts.append(
            f"--- [{i}] 관련도: {score:.2f} | {meta.get('filename', '')} p.{meta.get('page_number', '?')} ---\n"
            f"{result['text']}\n"
        )

    parts.append(
        "\n(※ LLM API 키가 설정되지 않아 검색 결과만 표시합니다. "
        "OPENAI_API_KEY를 설정하면 AI 요약 답변이 제공됩니다.)"
    )

    return "\n".join(parts)
