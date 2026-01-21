"""
Document ingestion module for RAG system.
Loads knowledge base documents and creates vector embeddings.
"""

import os
from pathlib import Path
from typing import List
import logging
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import sys

sys.path.append(str(Path(__file__).parent.parent))
from app.config import KNOWLEDGE_BASE_DIR, CHUNK_SIZE, CHUNK_OVERLAP
from rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)


class DocumentIngester:
    """Handles ingestion of documents into the vector store."""

    def __init__(self):
        """Initialize the document ingester."""
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def ingest_knowledge_base(self, force_recreate: bool = False) -> bool:
        """
        Ingest all documents from the knowledge base directory.

        Args:
            force_recreate: If True, delete existing vector store and recreate

        Returns:
            True if successful, False otherwise
        """
        vector_store = get_vector_store()

        # Check if vector store already exists
        if not force_recreate and vector_store.load_vector_store():
            logger.info("Vector store already exists, skipping ingestion")
            return True

        # Load documents
        documents = self.load_documents_from_directory(KNOWLEDGE_BASE_DIR)

        if not documents:
            logger.warning("No documents found to ingest")
            return False

        # Split documents into chunks
        split_docs = self.text_splitter.split_documents(documents)
        logger.info(f"Split {len(documents)} documents into {len(split_docs)} chunks")

        # Create vector store
        if force_recreate:
            vector_store.delete_vector_store()

        success = vector_store.create_vector_store(split_docs)

        if success:
            logger.info("Knowledge base ingestion completed successfully")
        else:
            logger.error("Knowledge base ingestion failed")

        return success

    def load_documents_from_directory(self, directory: Path) -> List[Document]:
        """
        Load all text documents from a directory.

        Args:
            directory: Path to directory containing text files

        Returns:
            List of LangChain Document objects
        """
        documents = []

        if not directory.exists():
            logger.warning(f"Directory does not exist: {directory}")
            return documents

        # Supported file extensions
        text_extensions = ['.txt', '.md', '.rst']

        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in text_extensions:
                try:
                    doc = self.load_document(file_path)
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    logger.error(f"Error loading {file_path}: {str(e)}")

        logger.info(f"Loaded {len(documents)} documents from {directory}")
        return documents

    def load_document(self, file_path: Path) -> Document:
        """
        Load a single document file.

        Args:
            file_path: Path to document file

        Returns:
            LangChain Document object
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            metadata = {
                "source": str(file_path.name),
                "file_path": str(file_path),
                "file_type": file_path.suffix,
            }

            return Document(page_content=content, metadata=metadata)

        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return None

    def ingest_text(self, text: str, metadata: dict = None) -> bool:
        """
        Ingest a single text string into the vector store.

        Args:
            text: Text content to ingest
            metadata: Optional metadata dictionary

        Returns:
            True if successful, False otherwise
        """
        if not text.strip():
            logger.warning("Cannot ingest empty text")
            return False

        vector_store = get_vector_store()

        # Ensure vector store is loaded
        if vector_store.vector_store is None:
            if not vector_store.load_vector_store():
                logger.error("Vector store not available")
                return False

        # Create document
        doc = Document(page_content=text, metadata=metadata or {})

        # Split if necessary
        split_docs = self.text_splitter.split_documents([doc])

        # Add to vector store
        return vector_store.add_documents(split_docs)


# Singleton instance
_ingester_instance = None


def get_document_ingester() -> DocumentIngester:
    """Get or create the DocumentIngester singleton."""
    global _ingester_instance
    if _ingester_instance is None:
        _ingester_instance = DocumentIngester()
    return _ingester_instance


def initialize_knowledge_base(force_recreate: bool = False) -> bool:
    """
    Initialize the knowledge base (convenience function).

    Args:
        force_recreate: If True, recreate vector store from scratch

    Returns:
        True if successful, False otherwise
    """
    ingester = get_document_ingester()
    return ingester.ingest_knowledge_base(force_recreate=force_recreate)
