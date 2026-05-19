"""
Session Management Module
Handles user sessions, chat history, and analytics.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
import uuid


class SessionManager:
    """
    Manages user sessions and persistent data.
    """
    
    def __init__(self, sessions_dir: str = 'sessions'):
        self.sessions_dir = sessions_dir
        self.active_sessions = {}
        
        # Create sessions directory if it doesn't exist
        os.makedirs(sessions_dir, exist_ok=True)
    
    def create_session(self, user_id: Optional[str] = None) -> str:
        """
        Create a new session.
        
        Args:
            user_id: Optional user identifier
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        
        session_data = {
            'session_id': session_id,
            'user_id': user_id or 'anonymous',
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'chat_history': [],
            'documents': [],
            'queries': [],
            'exports': []
        }
        
        self.active_sessions[session_id] = session_data
        self._save_session(session_id, session_data)
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data."""
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        
        # Try to load from disk
        return self._load_session(session_id)
    
    def add_chat_message(
        self,
        session_id: str,
        role: str,
        content: str,
        query_type: Optional[str] = None
    ) -> bool:
        """
        Add message to chat history.
        
        Args:
            session_id: Session ID
            role: 'user' or 'assistant'
            content: Message content
            query_type: Type of query (optional)
            
        Returns:
            Success status
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        message = {
            'timestamp': datetime.now().isoformat(),
            'role': role,
            'content': content,
            'query_type': query_type
        }
        
        session['chat_history'].append(message)
        session['last_activity'] = datetime.now().isoformat()
        self._save_session(session_id, session)
        
        return True
    
    def add_query(
        self,
        session_id: str,
        query: str,
        query_type: str,
        response: str,
        sources: List[str]
    ) -> bool:
        """
        Add query record to session.
        
        Args:
            session_id: Session ID
            query: Query text
            query_type: Type of query
            response: Generated response
            sources: Source documents
            
        Returns:
            Success status
        """
        session = self.get_session(session_id)
        if not session:
            return False
        
        query_record = {
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'query_type': query_type,
            'response': response,
            'sources': sources,
            'response_length': len(response),
            'source_count': len(sources)
        }
        
        session['queries'].append(query_record)
        session['last_activity'] = datetime.now().isoformat()
        self._save_session(session_id, session)
        
        return True
    
    def add_documents(
        self,
        session_id: str,
        filenames: List[str]
    ) -> bool:
        """Add uploaded documents to session."""
        session = self.get_session(session_id)
        if not session:
            return False
        
        for filename in filenames:
            if filename not in session['documents']:
                session['documents'].append({
                    'filename': filename,
                    'uploaded_at': datetime.now().isoformat()
                })
        
        self._save_session(session_id, session)
        return True
    
    def get_chat_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """Get chat history for session."""
        session = self.get_session(session_id)
        if not session:
            return []
        
        history = session['chat_history']
        return history[-limit:] if limit else history
    
    def get_query_history(
        self,
        session_id: str,
        query_type: Optional[str] = None
    ) -> List[Dict]:
        """Get query history, optionally filtered by type."""
        session = self.get_session(session_id)
        if not session:
            return []
        
        queries = session['queries']
        if query_type:
            queries = [q for q in queries if q['query_type'] == query_type]
        
        return queries
    
    def export_session(
        self,
        session_id: str,
        format_type: str = 'json'
    ) -> Optional[str]:
        """
        Export session data.
        
        Args:
            session_id: Session ID
            format_type: 'json' or 'markdown'
            
        Returns:
            Exported data as string
        """
        session = self.get_session(session_id)
        if not session:
            return None
        
        if format_type == 'json':
            return json.dumps(session, indent=2)
        
        elif format_type == 'markdown':
            return self._session_to_markdown(session)
        
        return None
    
    def get_session_stats(self, session_id: str) -> Optional[Dict]:
        """Get statistics for a session."""
        session = self.get_session(session_id)
        if not session:
            return None
        
        queries = session['queries']
        chat_history = session['chat_history']
        
        return {
            'session_id': session_id,
            'user_id': session['user_id'],
            'created_at': session['created_at'],
            'last_activity': session['last_activity'],
            'total_chats': len(chat_history),
            'total_queries': len(queries),
            'total_documents': len(session['documents']),
            'document_names': [d.get('filename') for d in session['documents']],
            'query_types': list(set(q['query_type'] for q in queries)),
            'average_response_length': round(
                sum(q['response_length'] for q in queries) / max(len(queries), 1), 2
            ),
            'average_sources_per_query': round(
                sum(q['source_count'] for q in queries) / max(len(queries), 1), 2
            )
        }
    
    def _save_session(self, session_id: str, data: Dict) -> None:
        """Save session to disk."""
        filepath = os.path.join(self.sessions_dir, f'{session_id}.json')
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_session(self, session_id: str) -> Optional[Dict]:
        """Load session from disk."""
        filepath = os.path.join(self.sessions_dir, f'{session_id}.json')
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
        return None
    
    def _session_to_markdown(self, session: Dict) -> str:
        """Convert session to markdown format."""
        md = f"""# Session Report: {session['session_id']}

**User ID:** {session['user_id']}
**Created:** {session['created_at']}
**Last Activity:** {session['last_activity']}

## Documents
"""
        for doc in session['documents']:
            md += f"- {doc['filename']} (uploaded: {doc['uploaded_at']})\n"
        
        md += "\n## Chat History\n"
        for msg in session['chat_history']:
            role = msg['role'].upper()
            md += f"\n**{role}** ({msg['timestamp']})\n{msg['content']}\n"
        
        md += "\n## Queries\n"
        for query in session['queries']:
            md += f"\n### {query['query_type'].upper()} - {query['timestamp']}\n"
            md += f"**Query:** {query['query']}\\n"
            md += f"**Response Length:** {query['response_length']} chars\n"
            md += f"**Sources:** {', '.join(query['sources'])}\n"
        
        return md
    
    def list_all_sessions(self) -> List[Dict]:
        """List all available sessions."""
        sessions = []
        for filename in os.listdir(self.sessions_dir):
            if filename.endswith('.json'):
                session_id = filename.replace('.json', '')
                data = self._load_session(session_id)
                if data:
                    sessions.append({
                        'session_id': session_id,
                        'user_id': data.get('user_id'),
                        'created_at': data.get('created_at'),
                        'last_activity': data.get('last_activity'),
                        'query_count': len(data.get('queries', []))
                    })
        
        return sorted(sessions, key=lambda x: x['created_at'], reverse=True)
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        filepath = os.path.join(self.sessions_dir, f'{session_id}.json')
        if os.path.exists(filepath):
            os.remove(filepath)
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            return True
        return False
