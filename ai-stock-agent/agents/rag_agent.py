"""
RAG Agent: Retrieves relevant market knowledge from vector database.
"""

from typing import List, Dict, Any
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from rag.vector_store import get_vector_store
from app.config import RAG_TOP_K

logger = logging.getLogger(__name__)


class RAGAgent:
    """Agent responsible for retrieving relevant market knowledge."""

    def __init__(self):
        """Initialize the RAG Agent."""
        self.vector_store = get_vector_store()
        self._ensure_vector_store_loaded()

    def _ensure_vector_store_loaded(self):
        """Ensure vector store is loaded and ready."""
        if self.vector_store.vector_store is None:
            logger.info("Loading vector store...")
            if not self.vector_store.load_vector_store():
                logger.warning("Vector store not found. Knowledge base may not be initialized.")

    def retrieve_context(
        self,
        features: Dict[str, Any],
        query_override: str = None,
        k: int = RAG_TOP_K
    ) -> str:
        """
        Retrieve relevant market knowledge based on technical features.

        Args:
            features: Dictionary of technical features from GraphFeatureAgent
            query_override: Optional custom query string (overrides automatic query generation)
            k: Number of documents to retrieve

        Returns:
            Formatted context string with retrieved knowledge
        """
        if self.vector_store.vector_store is None:
            logger.warning("Vector store not available, returning empty context")
            return "No historical market knowledge available."

        # Generate query based on features or use override
        if query_override:
            query = query_override
        else:
            query = self._generate_query_from_features(features)

        logger.info(f"RAG query: {query}")

        # Retrieve relevant documents
        try:
            documents = self.vector_store.similarity_search(query, k=k)

            if not documents:
                logger.warning("No relevant documents found")
                return "No relevant historical patterns found."

            # Format context
            context = self._format_context(documents)
            logger.info(f"Retrieved {len(documents)} relevant documents")

            return context

        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return "Error retrieving historical market knowledge."

    def _generate_query_from_features(self, features: Dict[str, Any]) -> str:
        """
        Generate a search query based on extracted technical features.

        Args:
            features: Technical feature dictionary

        Returns:
            Query string for vector search
        """
        query_parts = []

        # Add trend information
        trend = features.get("trend", "neutral")
        query_parts.append(f"{trend} trend")

        # Add momentum
        momentum = features.get("momentum", "neutral")
        if momentum != "neutral":
            query_parts.append(f"{momentum} momentum")

        # Add pattern if present
        pattern = features.get("pattern", "none")
        if pattern != "none":
            query_parts.append(pattern.replace("_", " "))

        # Add RSI signal
        rsi_signal = features.get("rsi_signal", "neutral")
        if rsi_signal != "neutral":
            query_parts.append(f"RSI {rsi_signal}")

        # Add MACD signal
        macd_signal = features.get("macd_signal", "neutral")
        if macd_signal != "neutral":
            query_parts.append(f"MACD {macd_signal}")

        # Add volatility
        volatility = features.get("volatility_level", "medium")
        query_parts.append(f"{volatility} volatility")

        # Add crossovers
        sma_crossover = features.get("sma_crossover", "none")
        if sma_crossover != "none":
            query_parts.append(f"moving average {sma_crossover.replace('_', ' ')}")

        # Combine into coherent query
        query = " ".join(query_parts)

        # Add context for better retrieval
        query += " stock market technical analysis pattern"

        return query

    def _format_context(self, documents: List) -> str:
        """
        Format retrieved documents into a context string.

        Args:
            documents: List of retrieved Document objects

        Returns:
            Formatted context string
        """
        context_parts = ["=== RELEVANT MARKET KNOWLEDGE ===\n"]

        for i, doc in enumerate(documents, 1):
            content = doc.page_content.strip()
            source = doc.metadata.get("source", "Unknown")

            context_parts.append(f"\n[Context {i} - Source: {source}]")
            context_parts.append(content)
            context_parts.append("")  # Empty line for spacing

        return "\n".join(context_parts)

    def retrieve_specific_topic(self, topic: str, k: int = RAG_TOP_K) -> str:
        """
        Retrieve knowledge about a specific topic.

        Args:
            topic: Topic to search for (e.g., "RSI divergence", "golden cross")
            k: Number of documents to retrieve

        Returns:
            Formatted context string
        """
        return self.retrieve_context(features={}, query_override=topic, k=k)

    def get_risk_guidelines(self) -> str:
        """
        Retrieve risk management guidelines.

        Returns:
            Risk guidelines context
        """
        return self.retrieve_specific_topic("risk management investment guidelines", k=2)


# Singleton instance
_rag_agent_instance = None


def get_rag_agent() -> RAGAgent:
    """Get or create the RAGAgent singleton."""
    global _rag_agent_instance
    if _rag_agent_instance is None:
        _rag_agent_instance = RAGAgent()
    return _rag_agent_instance
