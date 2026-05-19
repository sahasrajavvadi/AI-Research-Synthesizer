"""
Vector Store Module
Handles FAISS vector database for similarity search
"""

import faiss
import numpy as np
from typing import List, Tuple
import pickle
import os


class FAISSVectorStore:
    """
    Manages FAISS vector database for efficient similarity search.
    Stores embeddings and their corresponding metadata.
    """
    
    def __init__(self, embedding_dim: int):
        """
        Initialize FAISS vector store.
        
        Args:
            embedding_dim: Dimension of the embeddings (e.g., 384 for MiniLM)
        """
        print(f"[VECTOR_STORE] Initializing new vector store with dim={embedding_dim}")
        self.embedding_dim = embedding_dim
        self.index = faiss.IndexFlatL2(embedding_dim)  # L2 distance
        self.metadata = []  # Store chunk metadata
    
    def clear(self) -> None:
        """Completely clear the vector store."""
        print(f"[VECTOR_STORE] Clearing all data")
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.metadata = []
        print(f"[VECTOR_STORE] Vector store cleared. Total vectors: {self.index.ntotal}")
    
    def add_embeddings(self, embeddings: np.ndarray, metadata: List[dict]) -> None:
        """
        Add embeddings and their metadata to the vector store.
        
        Args:
            embeddings: 2D numpy array of embeddings (n_vectors, embedding_dim)
            metadata: List of metadata dictionaries corresponding to embeddings
        """
        print(f"[VECTOR_STORE] Adding {embeddings.shape[0]} embeddings")
        if embeddings.shape[0] != len(metadata):
            raise ValueError("Number of embeddings must match number of metadata items")
        
        embeddings = embeddings.astype(np.float32)
        print(f"[VECTOR_STORE] Embeddings shape: {embeddings.shape}")
        
        self.index.add(embeddings)
        print(f"[VECTOR_STORE] Added to FAISS index")
        
        self.metadata.extend(metadata)
        print(f"[VECTOR_STORE] Total vectors: {self.index.ntotal}")
    
    def search(self, query_embedding: np.ndarray, k: int = 5, filter_source: str = None) -> List[Tuple[dict, float]]:
        """
        Search for similar embeddings.
        
        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            filter_source: Optional source filename to filter results
            
        Returns:
            List of (metadata, distance) tuples
        """
        print(f"[VECTOR_STORE] Starting search with k={k}, filter_source={filter_source}")

        # Guard: empty index
        if self.index.ntotal == 0:
            print("[VECTOR_STORE] Index is empty, returning []")
            return []

        query_embedding = query_embedding.astype(np.float32).reshape(1, -1)
        print(f"[VECTOR_STORE] Query embedding shape: {query_embedding.shape}")

        # Normalize the filter path if provided
        filter_source_norm = None
        if filter_source:
            filter_source_norm = os.path.normpath(filter_source)
            print(f"[VECTOR_STORE] Normalized filter_source: {filter_source_norm}")

        # ------------------------------------------------------------------ #
        # CRITICAL FIX: When filtering by source we MUST search the ENTIRE   #
        # index first, otherwise top-k results might all come from one doc    #
        # and the target document would return 0 results.                     #
        # ------------------------------------------------------------------ #
        if filter_source_norm:
            # Search ALL vectors so we can find the best k from this source
            search_k = self.index.ntotal
        else:
            search_k = k

        search_k = min(search_k, self.index.ntotal)
        distances, indices = self.index.search(query_embedding, search_k)
        print(f"[VECTOR_STORE] Searched {search_k} candidates from index")

        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            meta = self.metadata[idx]

            # Normalize the stored path before comparing
            stored_source_norm = os.path.normpath(meta['source'])

            if filter_source_norm and stored_source_norm != filter_source_norm:
                continue

            results.append((meta, float(distance)))
            print(f"[VECTOR_STORE] Result: source={meta['source']}, chunk={meta['chunk_id']}, distance={distance:.4f}")
            if len(results) >= k:
                break

        print(f"[VECTOR_STORE] Returning {len(results)} valid results")
        return results

    
    def save(self, filepath: str) -> None:
        """
        Save the vector store to disk.
        
        Args:
            filepath: Path to save the vector store
        """
        # Save FAISS index
        index_path = filepath + ".index"
        faiss.write_index(self.index, index_path)
        
        # Save metadata
        metadata_path = filepath + ".metadata"
        with open(metadata_path, 'wb') as f:
            pickle.dump(self.metadata, f)
    
    def load(self, filepath: str) -> None:
        """
        Load vector store from disk.
        
        Args:
            filepath: Path to load the vector store from
        """
        # Load FAISS index
        index_path = filepath + ".index"
        self.index = faiss.read_index(index_path)
        
        # Load metadata
        metadata_path = filepath + ".metadata"
        with open(metadata_path, 'rb') as f:
            self.metadata = pickle.load(f)
    
    def get_stats(self) -> dict:
        """Get statistics about the vector store."""
        return {
            "total_vectors": self.index.ntotal,
            "embedding_dimension": self.embedding_dim,
            "total_chunks": len(self.metadata)
        }
