"""
Vector Store module for RAG system.
Handles document embedding and similarity search.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from langchain_community.vectorstores import FAISS, Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
import sys

sys.path.append(str(Path(__file__).parent.parent))
from app.config import (
    VECTOR_DB_TYPE, VECTOR_STORE_PATH, LLM_PROVIDER,
    EMBEDDING_MODEL, RAG_TOP_K
)

logger = logging.getLogger(__name__)


class VectorStore:
    """Manages vector database for RAG retrieval."""

    def __init__(self):
        """Initialize the vector store."""
        self.embeddings = self._get_embeddings()
        self.vector_store = None
        self.db_type = VECTOR_DB_TYPE

    def _get_embeddings(self):
        """Get embeddings model based on configuration."""
        if LLM_PROVIDER == "openai":
            return OpenAIEmbeddings(model=EMBEDDING_MODEL)
        elif LLM_PROVIDER == "anthropic":
            # Anthropic doesn't have native embeddings, fall back to OpenAI
            logger.warning("Using OpenAI embeddings (Anthropic doesn't provide embeddings)")
            return OpenAIEmbeddings(model=EMBEDDING_MODEL)
        else:
            raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")

    def create_vector_store(self, documents: List[Document]) -> bool:
        """
        Create a new vector store from documents.

        Args:
            documents: List of LangChain Document objects

        Returns:
            True if successful, False otherwise
        """
        if not documents:
            logger.error("Cannot create vector store with empty documents")
            return False

        try:
            logger.info(f"Creating {self.db_type} vector store with {len(documents)} documents")

            if self.db_type == "faiss":
                self.vector_store = FAISS.from_documents(documents, self.embeddings)
                # Save to disk
                self.vector_store.save_local(str(VECTOR_STORE_PATH))
                logger.info(f"FAISS vector store saved to {VECTOR_STORE_PATH}")

            elif self.db_type == "chroma":
                persist_directory = str(VECTOR_STORE_PATH)
                self.vector_store = Chroma.from_documents(
                    documents,
                    self.embeddings,
                    persist_directory=persist_directory
                )
                logger.info(f"Chroma vector store saved to {persist_directory}")

            else:
                raise ValueError(f"Unsupported vector DB type: {self.db_type}")

            return True

        except Exception as e:
            logger.error(f"Error creating vector store: {str(e)}")
            return False

    def load_vector_store(self) -> bool:
        """
        Load existing vector store from disk.

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.db_type == "faiss":
                if not (VECTOR_STORE_PATH / "index.faiss").exists():
                    logger.warning("FAISS index not found")
                    return False

                self.vector_store = FAISS.load_local(
                    str(VECTOR_STORE_PATH),
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.info("FAISS vector store loaded successfully")

            elif self.db_type == "chroma":
                if not VECTOR_STORE_PATH.exists():
                    logger.warning("Chroma database not found")
                    return False

                self.vector_store = Chroma(
                    persist_directory=str(VECTOR_STORE_PATH),
                    embedding_function=self.embeddings
                )
                logger.info("Chroma vector store loaded successfully")

            else:
                raise ValueError(f"Unsupported vector DB type: {self.db_type}")

            return True

        except Exception as e:
            logger.error(f"Error loading vector store: {str(e)}")
            return False

    def similarity_search(
        self,
        query: str,
        k: int = RAG_TOP_K,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Perform similarity search on the vector store.

        Args:
            query: Search query string
            k: Number of results to return
            filter_dict: Optional metadata filters

        Returns:
            List of matching Document objects
        """
        if self.vector_store is None:
            logger.error("Vector store not initialized")
            return []

        try:
            if filter_dict:
                results = self.vector_store.similarity_search(
                    query,
                    k=k,
                    filter=filter_dict
                )
            else:
                results = self.vector_store.similarity_search(query, k=k)

            logger.info(f"Found {len(results)} similar documents for query: {query[:50]}...")
            return results

        except Exception as e:
            logger.error(f"Error during similarity search: {str(e)}")
            return []

    def similarity_search_with_score(
        self,
        query: str,
        k: int = RAG_TOP_K
    ) -> List[tuple[Document, float]]:
        """
        Perform similarity search with relevance scores.

        Args:
            query: Search query string
            k: Number of results to return

        Returns:
            List of (Document, score) tuples
        """
        if self.vector_store is None:
            logger.error("Vector store not initialized")
            return []

        try:
            results = self.vector_store.similarity_search_with_score(query, k=k)
            logger.info(f"Found {len(results)} documents with scores")
            return results

        except Exception as e:
            logger.error(f"Error during similarity search with score: {str(e)}")
            return []

    def add_documents(self, documents: List[Document]) -> bool:
        """
        Add new documents to existing vector store.

        Args:
            documents: List of Document objects to add

        Returns:
            True if successful, False otherwise
        """
        if self.vector_store is None:
            logger.error("Vector store not initialized")
            return False

        try:
            self.vector_store.add_documents(documents)
            logger.info(f"Added {len(documents)} documents to vector store")

            # Save changes
            if self.db_type == "faiss":
                self.vector_store.save_local(str(VECTOR_STORE_PATH))

            return True

        except Exception as e:
            logger.error(f"Error adding documents: {str(e)}")
            return False

    def delete_vector_store(self) -> bool:
        """
        Delete the vector store from disk.

        Returns:
            True if successful, False otherwise
        """
        try:
            if VECTOR_STORE_PATH.exists():
                import shutil
                shutil.rmtree(VECTOR_STORE_PATH)
                logger.info("Vector store deleted")
                self.vector_store = None
                return True
            return False

        except Exception as e:
            logger.error(f"Error deleting vector store: {str(e)}")
            return False


# Singleton instance
_vector_store_instance = None


def get_vector_store() -> VectorStore:
    """Get or create the VectorStore singleton."""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance
