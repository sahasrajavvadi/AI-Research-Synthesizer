"""
Advanced Features Module
Provides enhanced RAG capabilities: advanced search, analytics, export, etc.
"""

import json
from typing import List, Dict, Tuple, Optional
from collections import Counter
from datetime import datetime
import re


class AdvancedSearchEngine:
    """
    Advanced search with filtering, pagination, and semantic search.
    """
    
    def __init__(self):
        self.search_history = []
    
    def semantic_search(
        self,
        query: str,
        vector_store,
        embeddings,
        k: int = 10,
        source_filter: Optional[str] = None,
        min_similarity: float = 0.3
    ) -> List[Dict]:
        """
        Semantic search with filtering and similarity threshold.
        
        Args:
            query: Search query
            vector_store: FAISS vector store
            embeddings: Embedding engine
            k: Number of results
            source_filter: Filter by document source
            min_similarity: Minimum similarity score
            
        Returns:
            List of matching chunks with metadata and scores
        """
        query_embedding = embeddings.embed_text(query)
        results = vector_store.search(
            query_embedding,
            k=k,
            filter_source=source_filter
        )
        
        # Log search
        self.search_history.append({
            'query': query,
            'timestamp': datetime.now().isoformat(),
            'results_count': len(results),
            'source_filter': source_filter
        })
        
        return [
            {
                'content': result[0]['content'],
                'source': result[0]['source'],
                'chunk_id': result[0]['chunk_id'],
                'similarity_score': float(result[1])
            }
            for result in results
        ]
    
    def keyword_search(
        self,
        keyword: str,
        chunks: List[str],
        metadata: List[Dict],
        case_sensitive: bool = False
    ) -> List[Dict]:
        """
        Simple keyword search across chunks.
        
        Args:
            keyword: Keyword to search
            chunks: List of text chunks
            metadata: Metadata for chunks
            case_sensitive: Case-sensitive search
            
        Returns:
            Matching chunks
        """
        results = []
        search_term = keyword if case_sensitive else keyword.lower()
        
        for i, chunk in enumerate(chunks):
            chunk_text = chunk if case_sensitive else chunk.lower()
            if search_term in chunk_text:
                results.append({
                    'content': chunk,
                    'source': metadata[i].get('source', 'unknown'),
                    'chunk_id': metadata[i].get('chunk_id', i),
                    'occurrence_count': chunk_text.count(search_term)
                })
        
        return sorted(results, key=lambda x: x['occurrence_count'], reverse=True)


class KeywordExtractor:
    """
    Extract and analyze keywords from documents.
    """
    
    @staticmethod
    def extract_keywords(
        text: str,
        min_freq: int = 2,
        min_length: int = 3
    ) -> List[Tuple[str, int]]:
        """
        Extract keywords from text based on frequency.
        
        Args:
            text: Input text
            min_freq: Minimum frequency threshold
            min_length: Minimum keyword length
            
        Returns:
            List of (keyword, frequency) tuples
        """
        # Clean and tokenize
        text = text.lower()
        words = re.findall(r'\b[a-z]+\b', text)
        
        # Filter stop words and short words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'was', 'are', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those',
            'i', 'you', 'he', 'she', 'it', 'we', 'they', 'what', 'which', 'who'
        }
        
        words = [w for w in words if w not in stop_words and len(w) >= min_length]
        
        # Count frequencies
        freq = Counter(words)
        
        return [
            (word, count) for word, count in freq.most_common()
            if count >= min_freq
        ]
    
    @staticmethod
    def extract_from_documents(
        chunks: List[str],
        top_k: int = 20
    ) -> Dict[str, int]:
        """
        Extract top keywords from multiple documents.
        
        Args:
            chunks: List of document chunks
            top_k: Number of top keywords to return
            
        Returns:
            Dictionary of keywords and frequencies
        """
        all_text = ' '.join(chunks)
        keywords = KeywordExtractor.extract_keywords(all_text, min_freq=1)
        return {word: count for word, count in keywords[:top_k]}


class CitationExporter:
    """
    Export citations in multiple formats (BibTeX, APA, MLA, Chicago).
    """
    
    @staticmethod
    def to_bibtex(
        title: str,
        authors: List[str],
        year: str,
        source: str
    ) -> str:
        """Generate BibTeX format citation."""
        author_str = ' and '.join(authors) if authors else 'Unknown'
        key = source.replace('.pdf', '').replace(' ', '_').lower()
        
        return f"""@article{{{key},
    author = {{{author_str}}},
    title = {{{title}}},
    year = {{{year}}},
    source = {{{source}}}
}}"""
    
    @staticmethod
    def to_apa(
        title: str,
        authors: List[str],
        year: str,
        source: str
    ) -> str:
        """Generate APA format citation."""
        if not authors:
            authors = ['Unknown']
        
        if len(authors) == 1:
            author_str = authors[0]
        elif len(authors) == 2:
            author_str = f"{authors[0]} & {authors[1]}"
        else:
            author_str = f"{authors[0]} et al."
        
        return f"{author_str} ({year}). {title}. {source}."
    
    @staticmethod
    def to_mla(
        title: str,
        authors: List[str],
        year: str,
        source: str
    ) -> str:
        """Generate MLA format citation."""
        if not authors:
            authors = ['Unknown']
        
        author_str = ', '.join(authors)
        return f"{author_str}. \"{title}.\" {source}, {year}."
    
    @staticmethod
    def to_chicago(
        title: str,
        authors: List[str],
        year: str,
        source: str
    ) -> str:
        """Generate Chicago format citation."""
        if not authors:
            authors = ['Unknown']
        
        author_str = ', '.join(authors)
        return f"{author_str}. \"{title}.\" {source} ({year})."
    
    @staticmethod
    def generate_bibliography(
        documents: List[Dict],
        format_type: str = 'apa'
    ) -> str:
        """
        Generate complete bibliography.
        
        Args:
            documents: List of document dicts with title, authors, year, source
            format_type: 'apa', 'bibtex', 'mla', 'chicago'
            
        Returns:
            Formatted bibliography string
        """
        format_methods = {
            'apa': CitationExporter.to_apa,
            'bibtex': CitationExporter.to_bibtex,
            'mla': CitationExporter.to_mla,
            'chicago': CitationExporter.to_chicago
        }
        
        formatter = format_methods.get(format_type.lower(), CitationExporter.to_apa)
        
        citations = []
        for doc in documents:
            citation = formatter(
                doc.get('title', 'Untitled'),
                doc.get('authors', []),
                doc.get('year', 'N.D.'),
                doc.get('source', 'Unknown')
            )
            citations.append(citation)
        
        return '\n\n'.join(citations)


class DocumentAnalytics:
    """
    Provide analytics and statistics about documents.
    """
    
    @staticmethod
    def calculate_document_stats(
        chunks: List[str],
        metadata: List[Dict]
    ) -> Dict:
        """
        Calculate comprehensive statistics.
        
        Args:
            chunks: List of document chunks
            metadata: Metadata for chunks
            
        Returns:
            Statistics dictionary
        """
        # Count by source
        sources = Counter([m.get('source', 'unknown') for m in metadata])
        
        # Word statistics
        total_words = sum(len(chunk.split()) for chunk in chunks)
        total_chars = sum(len(chunk) for chunk in chunks)
        avg_chunk_words = total_words / len(chunks) if chunks else 0
        avg_chunk_chars = total_chars / len(chunks) if chunks else 0
        
        # Uniqueness
        unique_words = len(set(' '.join(chunks).lower().split()))
        
        return {
            'total_chunks': len(chunks),
            'total_words': total_words,
            'total_characters': total_chars,
            'average_chunk_words': round(avg_chunk_words, 2),
            'average_chunk_characters': round(avg_chunk_chars, 2),
            'unique_words': unique_words,
            'documents': dict(sources),
            'document_count': len(sources),
            'vocabulary_richness': round(unique_words / max(total_words, 1), 4)
        }
    
    @staticmethod
    def get_document_timeline(
        metadata: List[Dict]
    ) -> Dict[str, int]:
        """
        Group documents by upload date.
        
        Args:
            metadata: Metadata with timestamps
            
        Returns:
            Timeline dictionary
        """
        timeline = Counter()
        
        for meta in metadata:
            if 'timestamp' in meta:
                date = meta['timestamp'].split('T')[0]
                timeline[date] += 1
        
        return dict(sorted(timeline.items()))


class DocumentSimilarity:
    """
    Detect duplicate and similar documents.
    """
    
    @staticmethod
    def calculate_jaccard_similarity(
        set1: set,
        set2: set
    ) -> float:
        """Calculate Jaccard similarity between two sets."""
        if not set1 and not set2:
            return 1.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    @staticmethod
    def detect_similar_documents(
        chunks: List[str],
        metadata: List[Dict],
        threshold: float = 0.7
    ) -> List[Dict]:
        """
        Detect documents with similar content.
        
        Args:
            chunks: Document chunks
            metadata: Metadata
            threshold: Similarity threshold (0-1)
            
        Returns:
            List of similar document pairs
        """
        # Group chunks by source
        doc_chunks = {}
        for i, meta in enumerate(metadata):
            source = meta.get('source', 'unknown')
            if source not in doc_chunks:
                doc_chunks[source] = []
            doc_chunks[source].append(chunks[i])
        
        # Calculate similarity
        sources = list(doc_chunks.keys())
        similar_pairs = []
        
        for i, source1 in enumerate(sources):
            for source2 in sources[i+1:]:
                # Create word sets
                words1 = set(' '.join(doc_chunks[source1]).lower().split())
                words2 = set(' '.join(doc_chunks[source2]).lower().split())
                
                similarity = DocumentSimilarity.calculate_jaccard_similarity(words1, words2)
                
                if similarity >= threshold:
                    similar_pairs.append({
                        'document1': source1,
                        'document2': source2,
                        'similarity_score': round(similarity, 3)
                    })
        
        return sorted(
            similar_pairs,
            key=lambda x: x['similarity_score'],
            reverse=True
        )
