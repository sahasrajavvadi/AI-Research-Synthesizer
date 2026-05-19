"""
Embedding Module
Handles text embedding using SentenceTransformers
"""

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List
import os


class EmbeddingEngine:
    """
    Manages text embeddings using SentenceTransformers.
    Uses a lightweight, fast model that runs locally.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding engine.
        
        Args:
            model_name: Name of the SentenceTransformer model to use
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Embed a single text string.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as numpy array
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """
        Embed multiple texts efficiently in batch.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            2D numpy array of embeddings (n_texts, embedding_dim)
        """
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model."""
        return self.embedding_dim


# Global embedding engine instance
_embedding_engine = None


def get_embedding_engine() -> EmbeddingEngine:
    """
    Get or create the global embedding engine instance.
    Uses lazy initialization for efficiency.
    """
    global _embedding_engine
    if _embedding_engine is None:
        _embedding_engine = EmbeddingEngine()
    return _embedding_engine


def embed_chunks(chunks: List[str]) -> np.ndarray:
    """
    Convenience function to embed a list of text chunks.
    
    Args:
        chunks: List of text chunks
        
    Returns:
        2D numpy array of embeddings
    """
    engine = get_embedding_engine()
    return engine.embed_texts(chunks)
