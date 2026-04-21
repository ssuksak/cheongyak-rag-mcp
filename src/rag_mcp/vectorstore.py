"""Vector store management using ChromaDB with Korean embeddings."""

import logging
from typing import Any

import chromadb
from chromadb.utils import embedding_functions

from .chunker import Chunk
from .config import get_config

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self):
        self.config = get_config()
        self.client = chromadb.PersistentClient(path=self.config.chroma_persist_dir)
        self._embedding_fn = None
        self._collection = None

    def _get_embedding_function(self):
        if self._embedding_fn is not None:
            return self._embedding_fn

        model_name = self.config.embedding_model
        logger.info(f"Loading embedding model: {model_name}")

        if model_name.startswith("text-embedding"):
            self._embedding_fn = embedding_functions.OpenAIEmbeddingFunction(
                api_key=self.config.openai_api_key,
                model_name=model_name,
            )
        else:
            self._embedding_fn = (
                embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=model_name,
                )
            )

        return self._embedding_fn

    def _get_collection(self):
        if self._collection is not None:
            return self._collection

        self._collection = self.client.get_or_create_collection(
            name=self.config.collection_name,
            embedding_function=self._get_embedding_function(),
            metadata={"hnsw:space": "cosine"},
        )
        return self._collection

    def add_chunks(self, chunks: list[Chunk]) -> int:
        if not chunks:
            return 0

        collection = self._get_collection()

        existing = collection.get(
            where={"filepath": chunks[0].document_filepath},
            include=["metadatas"],
        )
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
            logger.info(
                f"Removed {len(existing['ids'])} existing chunks for {chunks[0].document_filename}"
            )

        batch_size = 100
        total_added = 0

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            ids = [c.chunk_id for c in batch]
            documents = [c.text for c in batch]
            metadatas = [
                {
                    **c.metadata,
                    "char_count": c.char_count,
                }
                for c in batch
            ]

            collection.add(ids=ids, documents=documents, metadatas=metadatas)
            total_added += len(batch)

        logger.info(f"Added {total_added} chunks from {chunks[0].document_filename}")
        return total_added

    def search(
        self, query: str, top_k: int | None = None, filter_filename: str | None = None
    ) -> list[dict[str, Any]]:
        top_k = top_k or self.config.search_top_k
        collection = self._get_collection()

        where_filter = None
        if filter_filename:
            where_filter = {"filename": filter_filename}

        count = collection.count()
        if count == 0:
            return []

        actual_k = min(top_k, count)

        results = collection.query(
            query_texts=[query],
            n_results=actual_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        if not results["ids"][0]:
            return []

        search_results = []
        for i, doc_id in enumerate(results["ids"][0]):
            search_results.append(
                {
                    "chunk_id": doc_id,
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                    "relevance_score": round(1 - results["distances"][0][i], 4),
                }
            )

        return search_results

    def list_documents(self) -> list[dict[str, Any]]:
        collection = self._get_collection()

        if collection.count() == 0:
            return []

        all_data = collection.get(include=["metadatas"])

        doc_map: dict[str, dict[str, Any]] = {}
        for metadata in all_data["metadatas"]:
            filename = metadata.get("filename", "unknown")
            filepath = metadata.get("filepath", "")

            if filename not in doc_map:
                doc_map[filename] = {
                    "filename": filename,
                    "filepath": filepath,
                    "file_type": metadata.get("file_type", ""),
                    "chunk_count": 0,
                    "title": metadata.get("title", ""),
                }
            doc_map[filename]["chunk_count"] += 1

        return list(doc_map.values())

    def delete_document(self, filename: str) -> int:
        collection = self._get_collection()

        existing = collection.get(
            where={"filename": filename},
            include=["metadatas"],
        )

        if not existing["ids"]:
            return 0

        collection.delete(ids=existing["ids"])
        logger.info(f"Deleted {len(existing['ids'])} chunks for {filename}")
        return len(existing["ids"])

    def get_stats(self) -> dict[str, Any]:
        collection = self._get_collection()
        documents = self.list_documents()

        return {
            "total_chunks": collection.count(),
            "total_documents": len(documents),
            "documents": documents,
            "collection_name": self.config.collection_name,
            "embedding_model": self.config.embedding_model,
        }
