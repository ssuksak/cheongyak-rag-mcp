"""Configuration for 청약 RAG MCP Server."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .setup import get_env_file, is_first_run

_global_env_loaded = False


def _load_global_env():
    global _global_env_loaded
    if _global_env_loaded:
        return
    env_file = get_env_file()
    if os.path.exists(env_file):
        load_dotenv(env_file)
    load_dotenv()
    _global_env_loaded = True


_load_global_env()


@dataclass
class Config:
    applyhome_base_url: str = "https://www.applyhome.co.kr"
    data_go_kr_api_key: str = os.getenv("DATA_GO_KR_API_KEY", "")
    data_go_kr_base_url: str = "https://api.data.go.kr/openapi"
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "jhgan/ko-sroberta-multitask")
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
    documents_dir: str = os.getenv("DOCUMENTS_DIR", "./data/documents")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "1000"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    search_top_k: int = int(os.getenv("SEARCH_TOP_K", "5"))
    cache_ttl_minutes: int = int(os.getenv("CACHE_TTL_MINUTES", "30"))
    collection_name: str = "cheongyak"

    def __post_init__(self):
        Path(self.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
        Path(self.documents_dir).mkdir(parents=True, exist_ok=True)


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
