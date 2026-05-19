"""
Document Manager Module
Handles document metadata, versioning, and management.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import hashlib


class DocumentManager:
    """
    Manages document metadata and lifecycle.
    """
    
    def __init__(self, metadata_dir: str = 'data/metadata'):
        self.metadata_dir = metadata_dir
        self.documents = {}
        
        os.makedirs(metadata_dir, exist_ok=True)
        self._load_all_metadata()
    
    def register_document(
        self,
        filename: str,
        original_filename: str,
        file_size: int,
        chunk_count: int,
        upload_user: str = 'anonymous'
    ) -> Dict:
        """
        Register a new document.
        
        Args:
            filename: Stored filename
            original_filename: Original filename
            file_size: File size in bytes
            chunk_count: Number of chunks created
            upload_user: User who uploaded
            
        Returns:
            Document metadata
        """
        doc_id = hashlib.md5(f"{filename}{datetime.now().isoformat()}".encode()).hexdigest()
        
        metadata = {
            'doc_id': doc_id,
            'filename': filename,
            'original_filename': original_filename,
            'file_size': file_size,
            'chunk_count': chunk_count,
            'uploaded_at': datetime.now().isoformat(),
            'uploaded_by': upload_user,
            'status': 'active',
            'keywords': [],
            'word_count': 0,
            'language': 'en',
            'access_count': 0,
            'last_accessed': None,
            'tags': [],
            'notes': ''
        }
        
        self.documents[doc_id] = metadata
        self._save_metadata(doc_id, metadata)
        
        return metadata
    
    def get_document(self, doc_id: str) -> Optional[Dict]:
        """Get document metadata."""
        return self.documents.get(doc_id)
    
    def update_document_metadata(
        self,
        doc_id: str,
        **kwargs
    ) -> Optional[Dict]:
        """
        Update document metadata.
        
        Args:
            doc_id: Document ID
            **kwargs: Metadata fields to update
            
        Returns:
            Updated metadata
        """
        if doc_id not in self.documents:
            return None
        
        metadata = self.documents[doc_id]
        
        # Only allow certain fields to be updated
        updatable_fields = {'keywords', 'tags', 'notes', 'language', 'word_count'}
        
        for key, value in kwargs.items():
            if key in updatable_fields:
                metadata[key] = value
        
        metadata['last_modified'] = datetime.now().isoformat()
        self._save_metadata(doc_id, metadata)
        
        return metadata
    
    def add_tags(self, doc_id: str, tags: List[str]) -> bool:
        """Add tags to document."""
        if doc_id not in self.documents:
            return False
        
        metadata = self.documents[doc_id]
        metadata['tags'] = list(set(metadata.get('tags', []) + tags))
        self._save_metadata(doc_id, metadata)
        
        return True
    
    def set_notes(self, doc_id: str, notes: str) -> bool:
        """Set notes for document."""
        if doc_id not in self.documents:
            return False
        
        metadata = self.documents[doc_id]
        metadata['notes'] = notes
        self._save_metadata(doc_id, metadata)
        
        return True
    
    def record_access(self, doc_id: str) -> bool:
        """Record document access."""
        if doc_id not in self.documents:
            return False
        
        metadata = self.documents[doc_id]
        metadata['access_count'] = metadata.get('access_count', 0) + 1
        metadata['last_accessed'] = datetime.now().isoformat()
        self._save_metadata(doc_id, metadata)
        
        return True
    
    def get_all_documents(self) -> List[Dict]:
        """Get all documents."""
        return list(self.documents.values())
    
    def get_documents_by_tag(self, tag: str) -> List[Dict]:
        """Get documents with specific tag."""
        return [
            doc for doc in self.documents.values()
            if tag in doc.get('tags', [])
        ]
    
    def get_documents_by_user(self, user: str) -> List[Dict]:
        """Get documents uploaded by specific user."""
        return [
            doc for doc in self.documents.values()
            if doc.get('uploaded_by') == user
        ]
    
    def delete_document(self, doc_id: str) -> bool:
        """Mark document as deleted."""
        if doc_id not in self.documents:
            return False
        
        metadata = self.documents[doc_id]
        metadata['status'] = 'deleted'
        metadata['deleted_at'] = datetime.now().isoformat()
        self._save_metadata(doc_id, metadata)
        
        return True
    
    def restore_document(self, doc_id: str) -> bool:
        """Restore deleted document."""
        if doc_id not in self.documents:
            return False
        
        metadata = self.documents[doc_id]
        metadata['status'] = 'active'
        if 'deleted_at' in metadata:
            del metadata['deleted_at']
        self._save_metadata(doc_id, metadata)
        
        return True
    
    def get_document_statistics(self) -> Dict:
        """Get statistics about all documents."""
        active_docs = [d for d in self.documents.values() if d['status'] == 'active']
        
        return {
            'total_documents': len(self.documents),
            'active_documents': len(active_docs),
            'deleted_documents': len(self.documents) - len(active_docs),
            'total_size_bytes': sum(d['file_size'] for d in active_docs),
            'total_chunks': sum(d['chunk_count'] for d in active_docs),
            'average_file_size': round(
                sum(d['file_size'] for d in active_docs) / max(len(active_docs), 1), 2
            ),
            'most_accessed': max(
                (d for d in active_docs),
                key=lambda x: x.get('access_count', 0),
                default=None
            ),
            'recently_uploaded': max(
                (d for d in active_docs),
                key=lambda x: x.get('uploaded_at', ''),
                default=None
            )
        }
    
    def get_storage_info(self) -> Dict:
        """Get storage information."""
        active_docs = [d for d in self.documents.values() if d['status'] == 'active']
        total_size = sum(d['file_size'] for d in active_docs)
        
        return {
            'total_documents': len(active_docs),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'document_breakdown': [
                {
                    'filename': d['original_filename'],
                    'size_bytes': d['file_size'],
                    'size_mb': round(d['file_size'] / (1024 * 1024), 2),
                    'chunks': d['chunk_count'],
                    'uploaded_at': d['uploaded_at']
                }
                for d in active_docs
            ]
        }
    
    def export_inventory(self, format_type: str = 'json') -> str:
        """
        Export document inventory.
        
        Args:
            format_type: 'json' or 'csv'
            
        Returns:
            Formatted inventory
        """
        active_docs = [d for d in self.documents.values() if d['status'] == 'active']
        
        if format_type == 'json':
            return json.dumps(active_docs, indent=2)
        
        elif format_type == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            if active_docs:
                writer = csv.DictWriter(output, fieldnames=active_docs[0].keys())
                writer.writeheader()
                writer.writerows(active_docs)
            
            return output.getvalue()
        
        return ''
    
    def _save_metadata(self, doc_id: str, metadata: Dict) -> None:
        """Save metadata to disk."""
        filepath = os.path.join(self.metadata_dir, f'{doc_id}.json')
        with open(filepath, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def _load_metadata(self, doc_id: str) -> Optional[Dict]:
        """Load metadata from disk."""
        filepath = os.path.join(self.metadata_dir, f'{doc_id}.json')
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return None
    
    def _load_all_metadata(self) -> None:
        """Load all metadata files from disk."""
        if os.path.exists(self.metadata_dir):
            for filename in os.listdir(self.metadata_dir):
                if filename.endswith('.json'):
                    doc_id = filename.replace('.json', '')
                    metadata = self._load_metadata(doc_id)
                    if metadata:
                        self.documents[doc_id] = metadata
