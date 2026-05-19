"""
Flask Backend for AI Research Synthesizer
RESTful API for RAG operations
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import tempfile
from dotenv import load_dotenv
import json
from werkzeug.utils import secure_filename
import io
from datetime import datetime

from pdf_loader import prepare_chunks_with_metadata
from embedder import embed_chunks, get_embedding_engine
from vector_store import FAISSVectorStore
from rag_pipeline import RAGPipeline
from advanced_features import (
    AdvancedSearchEngine, KeywordExtractor, CitationExporter,
    DocumentAnalytics, DocumentSimilarity
)
from session_manager import SessionManager
from document_manager import DocumentManager

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

# Global state
state = {
    'vector_store': None,
    'rag_pipeline': None,
    'embeddings': None,
    'docs_loaded': False,
    'chunk_data': [],
    'api_initialized': False,
    'current_session': None
}

# Initialize managers
session_manager = SessionManager('sessions')
document_manager = DocumentManager('data/metadata')
search_engine = AdvancedSearchEngine()
keyword_extractor = KeywordExtractor()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ============================================================================
# ROUTES - Frontend Pages
# ============================================================================

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/analyze')
def analyze():
    """Analysis page"""
    return render_template('analyze.html')

# ============================================================================
# API ROUTES - Backend Operations
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'ok',
        'api_initialized': state['api_initialized'],
        'docs_loaded': state['docs_loaded']
    })

@app.route('/api/init-api', methods=['POST'])
def init_api():
    """Initialize Gemini API"""
    try:
        print("[FLASK] init_api endpoint called")
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            print("[FLASK] ERROR: GEMINI_API_KEY not found")
            return jsonify({'error': 'GEMINI_API_KEY not found in .env'}), 400
        
        # Initialize RAG pipeline
        print("[FLASK] Initializing RAG pipeline")
        state['rag_pipeline'] = RAGPipeline(api_key)
        
        # Test connection
        print("[FLASK] Testing connection")
        if not state['rag_pipeline'].test_connection():
            print("[FLASK] ERROR: Failed to connect to Gemini API")
            return jsonify({'error': 'Failed to connect to Gemini API'}), 400
        
        # Initialize embeddings
        print("[FLASK] Initializing embeddings")
        state['embeddings'] = get_embedding_engine()
        state['api_initialized'] = True
        print("[FLASK] API initialization complete")
        
        return jsonify({
            'status': 'success',
            'message': 'API initialized successfully'
        })
    
    except Exception as e:
        print(f"[FLASK] ERROR in init_api: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload-pdfs', methods=['POST'])
def upload_pdfs():
    """Upload and process PDF files"""
    try:
        print("[FLASK] upload_pdfs endpoint called")
        if 'files' not in request.files:
            print("[FLASK] ERROR: No files in request")
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        
        if not files:
            print("[FLASK] ERROR: No files selected")
            return jsonify({'error': 'No files selected'}), 400
        
        # Save uploaded files
        print(f"[FLASK] Saving {len(files)} files")
        saved_files = []
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                saved_files.append(filepath)
                print(f"[FLASK] Saved: {filename}")
        
        if not saved_files:
            print("[FLASK] ERROR: No valid PDF files")
            return jsonify({'error': 'No valid PDF files found'}), 400
        
        # Extract chunks from PDFs
        print("[FLASK] Extracting chunks from PDFs")
        pdf_files = [open(f, 'rb') for f in saved_files]
        chunks_data = prepare_chunks_with_metadata(pdf_files)
        state['chunk_data'] = chunks_data
        
        # Close file handles
        for f in pdf_files:
            f.close()
        
        # Generate embeddings
        print("[FLASK] Generating embeddings")
        chunk_contents = [chunk["content"] for chunk in chunks_data]
        embeddings_array = embed_chunks(chunk_contents)
        
        # Create and populate vector store
        print("[FLASK] Creating vector store")
        embedding_dim = state['embeddings'].get_embedding_dimension()
        vector_store = FAISSVectorStore(embedding_dim)
        vector_store.add_embeddings(embeddings_array, chunks_data)
        
        state['vector_store'] = vector_store
        state['docs_loaded'] = True
        
        # Get stats
        stats = vector_store.get_stats()
        print(f"[FLASK] Upload complete: {stats['total_vectors']} vectors")
        
        # Log all unique sources
        unique_docs = list(set([chunk['source'] for chunk in chunks_data]))
        print(f"[FLASK] Unique documents loaded: {unique_docs}")
        print(f"[FLASK] Total unique documents: {len(unique_docs)}")
        
        return jsonify({
            'status': 'success',
            'message': f'Processed {len(saved_files)} PDF(s)',
            'chunks': stats['total_vectors'],
            'embedding_dimension': stats['embedding_dimension']
        })
    
    except Exception as e:
        print(f"[FLASK] ERROR in upload_pdfs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/synthesize', methods=['POST'])
def synthesize():
    """RAG-only: analyze question intent, retrieve from all relevant docs, synthesize. Accepts query only (type optional)."""
    try:
        print("[FLASK] synthesize endpoint called")
        if not state['docs_loaded']:
            print("[FLASK] ERROR: No documents loaded")
            return jsonify({'error': 'No documents loaded'}), 400
        
        data = request.json or {}
        query = (data.get('query') or '').strip()
        query_type_override = data.get('type') or None  # optional; if not set, backend infers from query
        print(f"[FLASK] query: '{query[:80] if query else 'N/A'}...', type_override: {query_type_override}")
        
        # Single RAG entry point: analyzes question and pulls from all documents when needed (e.g. "summarize all 3")
        answer, sources = state['rag_pipeline'].ask(
            query=query or "Summarize all documents.",
            vector_store=state['vector_store'],
            embeddings=state['embeddings'],
            k=12,
            query_type_override=query_type_override,
        )
        
        print(f"[FLASK] Synthesis complete, answer length: {len(answer)}, sources: {len(sources)}")
        
        # Log which documents were actually used
        docs_used = list(set([s['source'] for s in sources]))
        print(f"[FLASK] Documents used in response: {docs_used}")
        print(f"[FLASK] Total documents used: {len(docs_used)}")
        
        # Get all available documents
        all_docs = list(set([meta['source'] for meta in state['vector_store'].metadata]))
        print(f"[FLASK] All available documents: {all_docs}")
        print(f"[FLASK] Total available documents: {len(all_docs)}")
        
        # Warn if not all documents were used
        if len(docs_used) < len(all_docs):
            missing = set(all_docs) - set(docs_used)
            print(f"[FLASK] WARNING: These documents were NOT used: {missing}")
        
        # Deduplicate sources by filename
        unique_sources = []
        seen_files = set()
        for source in sources:
            filename = source['source']
            if filename not in seen_files:
                seen_files.add(filename)
                unique_sources.append(source)
        
        print(f"[FLASK] Unique sources in response: {len(unique_sources)}")
        
        return jsonify({
            'status': 'success',
            'answer': answer,
            'sources': unique_sources
        })
    
    except Exception as e:
        print(f"[FLASK] ERROR in synthesize: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download():
    """Download analysis results"""
    try:
        data = request.json
        answer = data.get('answer', '')
        sources = data.get('sources', [])
        analysis_type = data.get('type', 'synthesis')
        
        # Create text content
        content = f"{analysis_type.upper()}\n"
        content += "=" * 50 + "\n\n"
        content += answer + "\n\n"
        content += "SOURCES\n"
        content += "=" * 50 + "\n"
        for i, source in enumerate(sources, 1):
            content += f"{i}. {source['source']}\n"
        
        # Create BytesIO object
        bytes_io = io.BytesIO(content.encode('utf-8'))
        
        return send_file(
            bytes_io,
            mimetype='text/plain',
            as_attachment=True,
            download_name=f'research_synthesis_{analysis_type}.txt'
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear', methods=['POST'])
def clear():
    """Clear loaded documents"""
    print("[FLASK] Clearing all documents and vector store")
    
    # Clear vector store completely
    if state['vector_store'] is not None:
        state['vector_store'].clear()
    
    state['vector_store'] = None
    state['docs_loaded'] = False
    state['chunk_data'] = []
    
    # Clear uploaded files
    for file in os.listdir(app.config['UPLOAD_FOLDER']):
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file)
        os.remove(filepath)
        print(f"[FLASK] Deleted: {filepath}")
    
    print("[FLASK] All data cleared successfully")
    return jsonify({'status': 'success', 'message': 'Documents cleared'})

@app.route('/api/stats', methods=['GET'])
def stats():
    """Get system statistics"""
    if not state['docs_loaded']:
        return jsonify({'error': 'No documents loaded'}), 400
    
    stats_info = state['vector_store'].get_stats()
    return jsonify(stats_info)

# ============================================================================
# ADVANCED FEATURES - Search, Analytics, Export
# ============================================================================

@app.route('/api/search/semantic', methods=['POST'])
def semantic_search():
    """Advanced semantic search with filters"""
    try:
        if not state['docs_loaded']:
            return jsonify({'error': 'No documents loaded'}), 400
        
        data = request.json or {}
        query = data.get('query', '').strip()
        k = data.get('k', 10)
        source_filter = data.get('source_filter')
        
        if not query:
            return jsonify({'error': 'Query required'}), 400
        
        results = search_engine.semantic_search(
            query,
            state['vector_store'],
            state['embeddings'],
            k=k,
            source_filter=source_filter
        )
        
        return jsonify({
            'status': 'success',
            'query': query,
            'results_count': len(results),
            'results': results
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/search/keyword', methods=['POST'])
def keyword_search():
    """Keyword-based search"""
    try:
        if not state['docs_loaded']:
            return jsonify({'error': 'No documents loaded'}), 400
        
        data = request.json or {}
        keyword = data.get('keyword', '').strip()
        case_sensitive = data.get('case_sensitive', False)
        
        if not keyword:
            return jsonify({'error': 'Keyword required'}), 400
        
        chunks = [chunk["content"] for chunk in state['chunk_data']]
        metadata = [chunk for chunk in state['chunk_data']]
        
        results = search_engine.keyword_search(
            keyword, chunks, metadata, case_sensitive
        )
        
        return jsonify({
            'status': 'success',
            'keyword': keyword,
            'results_count': len(results),
            'results': results
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/keywords', methods=['GET'])
def extract_keywords():
    """Extract keywords from documents"""
    try:
        if not state['docs_loaded']:
            return jsonify({'error': 'No documents loaded'}), 400
        
        chunks = [chunk["content"] for chunk in state['chunk_data']]
        keywords = keyword_extractor.extract_from_documents(chunks, top_k=30)
        
        return jsonify({
            'status': 'success',
            'keywords': keywords
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/documents', methods=['GET'])
def document_analytics():
    """Get document analytics"""
    try:
        if not state['docs_loaded']:
            return jsonify({'error': 'No documents loaded'}), 400
        
        chunks = [chunk["content"] for chunk in state['chunk_data']]
        metadata = state['chunk_data']
        
        stats = DocumentAnalytics.calculate_document_stats(chunks, metadata)
        
        return jsonify({
            'status': 'success',
            'analytics': stats
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/similarity', methods=['GET'])
def detect_duplicate_documents():
    """Detect similar documents"""
    try:
        if not state['docs_loaded']:
            return jsonify({'error': 'No documents loaded'}), 400
        
        chunks = [chunk["content"] for chunk in state['chunk_data']]
        metadata = state['chunk_data']
        threshold = request.args.get('threshold', 0.7, type=float)
        
        similar = DocumentSimilarity.detect_similar_documents(
            chunks, metadata, threshold
        )
        
        return jsonify({
            'status': 'success',
            'similar_documents': similar,
            'threshold': threshold
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/citations', methods=['POST'])
def export_citations():
    """Export citations in various formats"""
    try:
        if not state['docs_loaded']:
            return jsonify({'error': 'No documents loaded'}), 400
        
        data = request.json or {}
        format_type = data.get('format', 'apa').lower()
        documents = data.get('documents', [])
        
        if format_type not in ['apa', 'bibtex', 'mla', 'chicago']:
            return jsonify({'error': 'Invalid format'}), 400
        
        bibliography = CitationExporter.generate_bibliography(
            documents, format_type
        )
        
        return jsonify({
            'status': 'success',
            'format': format_type,
            'bibliography': bibliography
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/results', methods=['POST'])
def export_results():
    """Export analysis results in multiple formats"""
    try:
        data = request.json or {}
        answer = data.get('answer', '')
        sources = data.get('sources', [])
        format_type = data.get('format', 'txt').lower()
        analysis_type = data.get('type', 'synthesis')
        
        if format_type == 'markdown':
            content = f"# {analysis_type.upper()}\n\n{answer}\n\n## Sources\n"
            for source in sources:
                content += f"- {source.get('source', 'Unknown')}\n"
        elif format_type == 'json':
            content = json.dumps({
                'type': analysis_type,
                'answer': answer,
                'sources': sources,
                'timestamp': datetime.now().isoformat()
            }, indent=2)
        else:  # txt
            content = f"{analysis_type.upper()}\n{'='*50}\n\n{answer}\n\n"
            content += "SOURCES\n" + "="*50 + "\n"
            for i, source in enumerate(sources, 1):
                content += f"{i}. {source.get('source', 'Unknown')}\n"
        
        bytes_io = io.BytesIO(content.encode('utf-8'))
        
        return send_file(
            bytes_io,
            mimetype='text/plain',
            as_attachment=True,
            download_name=f'research_{analysis_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.{format_type}'
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

@app.route('/api/session/create', methods=['POST'])
def create_session():
    """Create new session"""
    try:
        data = request.json or {}
        user_id = data.get('user_id', 'anonymous')
        
        session_id = session_manager.create_session(user_id)
        state['current_session'] = session_id
        
        return jsonify({
            'status': 'success',
            'session_id': session_id
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/chat', methods=['POST'])
def add_chat_message():
    """Add message to chat history"""
    try:
        if not state['current_session']:
            return jsonify({'error': 'No active session'}), 400
        
        data = request.json or {}
        role = data.get('role')
        content = data.get('content')
        query_type = data.get('query_type')
        
        success = session_manager.add_chat_message(
            state['current_session'], role, content, query_type
        )
        
        if not success:
            return jsonify({'error': 'Failed to add message'}), 400
        
        return jsonify({'status': 'success'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/history', methods=['GET'])
def get_chat_history():
    """Get chat history"""
    try:
        if not state['current_session']:
            return jsonify({'error': 'No active session'}), 400
        
        limit = request.args.get('limit', None, type=int)
        history = session_manager.get_chat_history(state['current_session'], limit)
        
        return jsonify({
            'status': 'success',
            'history': history
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/stats', methods=['GET'])
def get_session_stats():
    """Get current session statistics"""
    try:
        if not state['current_session']:
            return jsonify({'error': 'No active session'}), 400
        
        stats = session_manager.get_session_stats(state['current_session'])
        
        return jsonify({
            'status': 'success',
            'stats': stats
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/export', methods=['GET'])
def export_session():
    """Export current session"""
    try:
        if not state['current_session']:
            return jsonify({'error': 'No active session'}), 400
        
        format_type = request.args.get('format', 'json')
        exported = session_manager.export_session(state['current_session'], format_type)
        
        if not exported:
            return jsonify({'error': 'Failed to export session'}), 400
        
        bytes_io = io.BytesIO(exported.encode('utf-8'))
        
        return send_file(
            bytes_io,
            mimetype='text/plain',
            as_attachment=True,
            download_name=f'session_{state["current_session"][:8]}.{format_type}'
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# DOCUMENT MANAGEMENT
# ============================================================================

@app.route('/api/documents/inventory', methods=['GET'])
def get_documents_inventory():
    """Get document inventory"""
    try:
        documents = document_manager.get_all_documents()
        active_docs = [d for d in documents if d['status'] == 'active']
        
        return jsonify({
            'status': 'success',
            'total': len(documents),
            'active': len(active_docs),
            'documents': active_docs
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/documents/storage', methods=['GET'])
def get_storage_info():
    """Get storage information"""
    try:
        storage_info = document_manager.get_storage_info()
        
        return jsonify({
            'status': 'success',
            'storage': storage_info
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/documents/<doc_id>', methods=['GET'])
def get_document_metadata(doc_id):
    """Get specific document metadata"""
    try:
        doc = document_manager.get_document(doc_id)
        
        if not doc:
            return jsonify({'error': 'Document not found'}), 404
        
        return jsonify({
            'status': 'success',
            'document': doc
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/documents/<doc_id>/tags', methods=['POST'])
def add_document_tags(doc_id):
    """Add tags to document"""
    try:
        data = request.json or {}
        tags = data.get('tags', [])
        
        success = document_manager.add_tags(doc_id, tags)
        
        if not success:
            return jsonify({'error': 'Document not found'}), 404
        
        return jsonify({'status': 'success'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/documents/<doc_id>/notes', methods=['POST'])
def set_document_notes(doc_id):
    """Set notes for document"""
    try:
        data = request.json or {}
        notes = data.get('notes', '')
        
        success = document_manager.set_notes(doc_id, notes)
        
        if not success:
            return jsonify({'error': 'Document not found'}), 404
        
        return jsonify({'status': 'success'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================================================
# 🤖 RESEARCH AGENT ROUTES - Advanced Analysis Features
# ============================================================================

@app.route('/api/research-agent/extract-components', methods=['POST'])
def extract_research_components():
    """
    Extract all research components (problem, methodology, findings, gaps, etc.)
    from uploaded documents using AI agent
    """
    try:
        if not state['rag_pipeline'] or not state['docs_loaded']:
            return jsonify({'error': 'No documents loaded'}), 400
        
        print("🤖 [RESEARCH_AGENT] Extracting research components...")
        
        # Extract all components using research agent
        all_components = state['rag_pipeline'].extract_research_components(
            vector_store=state['vector_store'],
            embeddings=state['embeddings'],
            k=8
        )
        
        return jsonify({
            'status': 'success',
            'components': all_components,
            'documents_analyzed': len(all_components)
        })
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/research-agent/compare-component', methods=['POST'])
def compare_research_component():
    """
    Compare a specific component across all papers
    """
    try:
        data = request.json or {}
        component = data.get('component', 'methodology')
        all_components = data.get('components', {})
        
        if not all_components:
            return jsonify({'error': 'No components provided'}), 400
        
        print(f"📊 [RESEARCH_AGENT] Comparing {component}...")
        
        # Get comparison analysis
        comparison = state['rag_pipeline'].compare_research_components(
            all_papers_analysis=all_components,
            component=component
        )
        
        return jsonify({
            'status': 'success',
            'component': component,
            'comparison': comparison
        })
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/research-agent/identify-frontiers', methods=['POST'])
def identify_research_frontiers_route():
    """
    Identify emerging research frontiers and gaps across all papers
    """
    try:
        data = request.json or {}
        all_components = data.get('components', {})
        
        if not all_components:
            return jsonify({'error': 'No components provided'}), 400
        
        print("🚀 [RESEARCH_AGENT] Identifying research frontiers...")
        
        # Get frontier analysis
        frontiers = state['rag_pipeline'].identify_research_frontiers(
            all_papers_analysis=all_components
        )
        
        return jsonify({
            'status': 'success',
            'analysis': frontiers
        })
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/research-agent/research-summary', methods=['POST'])
def generate_research_summary():
    """
    Generate comprehensive research summary across all papers
    """
    try:
        data = request.json or {}
        all_components = data.get('components', {})
        focus_area = data.get('focus_area', 'contributions')
        
        if not all_components:
            return jsonify({'error': 'No components provided'}), 400
        
        print(f"📝 [RESEARCH_AGENT] Generating research summary (focus: {focus_area})...")
        
        # Generate summary
        summary = state['rag_pipeline'].generate_comprehensive_research_summary(
            all_papers_analysis=all_components,
            focus_area=focus_area
        )
        
        return jsonify({
            'status': 'success',
            'focus_area': focus_area,
            'summary': summary
        })
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/research-agent/full-analysis', methods=['GET'])
def full_research_analysis():
    """
    Run complete research analysis pipeline end-to-end
    """
    try:
        if not state['rag_pipeline'] or not state['docs_loaded']:
            return jsonify({'error': 'No documents loaded'}), 400
        
        print("🧠 [RESEARCH_AGENT] Starting full research analysis...")
        
        # Step 1: Extract all components
        print("Step 1: Extracting components...")
        all_components = state['rag_pipeline'].extract_research_components(
            vector_store=state['vector_store'],
            embeddings=state['embeddings'],
            k=8
        )
        
        # Step 2: Identify research frontiers
        print("Step 2: Identifying research frontiers...")
        frontiers = state['rag_pipeline'].identify_research_frontiers(
            all_papers_analysis=all_components
        )
        
        # Step 3: Generate methodology comparison
        print("Step 3: Comparing methodologies...")
        methodology_comparison = state['rag_pipeline'].compare_research_components(
            all_papers_analysis=all_components,
            component='methodology'
        )
        
        # Step 4: Generate findings summary
        print("Step 4: Summarizing findings...")
        findings_summary = state['rag_pipeline'].generate_comprehensive_research_summary(
            all_papers_analysis=all_components,
            focus_area='findings'
        )
        
        print("✅ Full analysis complete!")
        
        return jsonify({
            'status': 'success',
            'analysis': {
                'extracted_components': all_components,
                'research_frontiers': frontiers,
                'methodology_comparison': methodology_comparison,
                'findings_summary': findings_summary,
                'documents_analyzed': len(all_components)
            }
        })
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    # Ensure upload folder exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Run Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)