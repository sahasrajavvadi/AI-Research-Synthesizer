/* ============================================================================
   Analyze Page JavaScript
   ============================================================================ */

const API_BASE = '/api';

// State
let selectedFiles = [];
let analysisType = 'general';



// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    checkHealth();
});

function initializeEventListeners() {
    // API Initialization
    document.getElementById('initApiBtn')?.addEventListener('click', initializeAPI);
    
    // File Upload
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    
    if (uploadArea) {
        uploadArea.addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('dragover', handleDragOver);
        uploadArea.addEventListener('dragleave', handleDragLeave);
        uploadArea.addEventListener('drop', handleDrop);
    }
    
    fileInput?.addEventListener('change', handleFileSelect);
    
    // Process and Clear
    document.getElementById('processBtn')?.addEventListener('click', processDocuments);
    document.getElementById('clearBtn')?.addEventListener('click', clearDocuments);
    
    // Analysis
    document.getElementById('synthesizeBtn')?.addEventListener('click', performAnalysis);
    
    // Keyboard: Ctrl+Enter to submit
    document.getElementById('queryInput')?.addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'Enter') {
            e.preventDefault();
            performAnalysis();
        }
    });
    
    // Mic button
    document.getElementById('micBtn')?.addEventListener('click', toggleMic);
    
    // Copy answer
    document.getElementById('copyBtn')?.addEventListener('click', copyAnswerToClipboard);
    
    // Action Buttons (send type override + default query so backend uses correct RAG path)
    const defaultQueries = {
        gaps: 'What are the research gaps and limitations?',
        compare: 'Compare the methodologies across all documents.',
        summarize: 'Summarize all documents.',
        trends: 'Analyze trends and evolution across the documents.',
        table: 'Create a comparison table of all documents.',
        citations: 'Give me detailed citations from all documents.'
    };
    document.querySelectorAll('.action-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            analysisType = this.dataset.type;
            const query = defaultQueries[analysisType] || 'Summarize all documents.';
            performAnalysisType(analysisType, query);
        });
    });
    
    // Download
    document.getElementById('downloadBtn')?.addEventListener('click', downloadResults);
}

// ============================================================================
// Speech to Text (Web Speech API)
// ============================================================================



// ============================================================================
// Copy answer to clipboard
// ============================================================================

function copyAnswerToClipboard() {
    if (!window.currentResults) return;
    const text = window.currentResults.answer || '';
    if (!text) return;
    navigator.clipboard.writeText(text).then(function() {
        const btn = document.getElementById('copyBtn');
        if (btn) {
            const orig = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check"></i> Copied';
            btn.classList.add('copied');
            setTimeout(function() {
                btn.innerHTML = orig;
                btn.classList.remove('copied');
            }, 2000);
        }
    }).catch(function() {
        alert('Copy failed.');
    });
}

// ============================================================================
// Health Check
// ============================================================================

async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();
        
        if (data.docs_loaded) {
            showAnalysisSection();
        }
    } catch (error) {
        console.error('Health check failed:', error);
    }
}

// ============================================================================
// API Initialization
// ============================================================================

async function initializeAPI() {
    const btn = document.getElementById('initApiBtn');
    const status = document.getElementById('apiStatus');
    
    btn.disabled = true;
    showMessage(status, 'Initializing API...', 'info');
    
    try {
        const response = await fetch(`${API_BASE}/init-api`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showMessage(status, '✅ API initialized successfully!', 'success');
            document.getElementById('processBtn').disabled = false;
        } else {
            showMessage(status, `❌ ${data.error}`, 'error');
            btn.disabled = false;
        }
    } catch (error) {
        showMessage(status, `❌ Error: ${error.message}`, 'error');
        btn.disabled = false;
    }
}

// ============================================================================
// File Upload Handlers
// ============================================================================

function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById('uploadArea').classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById('uploadArea').classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById('uploadArea').classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    handleFileSelect({ target: { files } });
}

function handleFileSelect(event) {
    selectedFiles = Array.from(event.target.files).filter(f => f.type === 'application/pdf');
    updateFileList();
}

function updateFileList() {
    const fileList = document.getElementById('fileList');
    fileList.innerHTML = '';
    
    selectedFiles.forEach((file, index) => {
        const div = document.createElement('div');
        div.className = 'file-item';
        div.innerHTML = `
            <span><i class="fas fa-file-pdf"></i> ${file.name}</span>
            <button class="file-remove" data-index="${index}">
                <i class="fas fa-times"></i>
            </button>
        `;
        fileList.appendChild(div);
    });
    
    // Remove listeners
    document.querySelectorAll('.file-remove').forEach(btn => {
        btn.addEventListener('click', function() {
            selectedFiles.splice(this.dataset.index, 1);
            updateFileList();
        });
    });
}

// ============================================================================
// Document Processing
// ============================================================================

async function processDocuments() {
    if (selectedFiles.length === 0) {
        showMessage(document.getElementById('processStatus'), 'Please select PDF files', 'error');
        return;
    }
    
    const btn = document.getElementById('processBtn');
    const status = document.getElementById('processStatus');
    
    btn.disabled = true;
    showMessage(status, 'Processing documents...', 'info');
    
    try {
        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files', file);
        });
        
        const response = await fetch(`${API_BASE}/upload-pdfs`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showMessage(status, `✅ ${data.message} (${data.chunks} chunks)`, 'success');
            document.getElementById('clearBtn').style.display = 'block';
            showAnalysisSection();
            updateStats();
        } else {
            showMessage(status, `❌ ${data.error}`, 'error');
            btn.disabled = false;
        }
    } catch (error) {
        showMessage(status, `❌ Error: ${error.message}`, 'error');
        btn.disabled = false;
    }
}

async function clearDocuments() {
    try {
        await fetch(`${API_BASE}/clear`, { method: 'POST' });
        
        selectedFiles = [];
        updateFileList();
        document.getElementById('clearBtn').style.display = 'none';
        document.getElementById('processBtn').disabled = true;
        document.getElementById('resultsSection').style.display = 'none';
        document.getElementById('welcomeSection').style.display = 'block';
        document.getElementById('analysisSection').style.display = 'none';
        document.getElementById('statsSection').style.display = 'none';
    } catch (error) {
        console.error('Error clearing documents:', error);
    }
}

// ============================================================================
// Analysis
// ============================================================================

async function performAnalysis() {
    const query = (document.getElementById('queryInput').value || '').trim();
    // RAG mode: backend infers intent from question (e.g. "summarize all 3" -> summarize_all)
    if (!query) {
        alert('Please enter a question (e.g. "Summarize all my documents" or "What are the research gaps?")');
        return;
    }
    await performAnalysisType(null, query);
}

// type: optional override (e.g. from quick-action buttons). If null, backend infers from query.
async function performAnalysisType(type, query = '') {
    const loadingSpinner = document.getElementById('loadingSpinner');
    const resultsSection = document.getElementById('resultsSection');
    
    loadingSpinner.style.display = 'flex';
    resultsSection.style.display = 'none';
    
    const loadingTexts = {
        gaps: 'Analyzing research gaps...',
        compare: 'Comparing methods...',
        summarize: 'Summarizing all documents...',
        trends: 'Analyzing trends...',
        table: 'Generating comparison table...',
        citations: 'Generating citations...',
        general: 'Answering from your documents...'
    };
    
    document.getElementById('loadingText').textContent = loadingTexts[type] || 'Answering from your documents...';
    
    try {
        const body = { query: query || 'Summarize all documents.' };
        if (type) body.type = type;
        
        const response = await fetch(`${API_BASE}/synthesize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayResults(data.answer, data.sources, type || 'answer');
            resultsSection.style.display = 'block';
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (error) {
        alert(`Error: ${error.message}`);
    } finally {
        loadingSpinner.style.display = 'none';
    }
}

function displayResults(answer, sources, type) {
    // Display answer
    const answerContent = document.getElementById('answerContent');
    answerContent.innerHTML = markdownToHtml(answer);
    
    // Display sources
    const sourcesList = document.getElementById('sourcesList');
    sourcesList.innerHTML = '';
    
    sources.forEach((source, index) => {
        const div = document.createElement('div');
        div.className = 'source-item';
        div.innerHTML = `
            <strong>${index + 1}.</strong> ${source.source}
            ${source.relevance_score ? ` <em>(Relevance: ${(source.relevance_score * 100).toFixed(1)}%)</em>` : ''}
        `;
        sourcesList.appendChild(div);
    });
    
    // Store results for download
    window.currentResults = {
        answer: answer,
        sources: sources,
        type: type
    };
}

// ============================================================================
// Markdown to HTML (Simple conversion)
// ============================================================================

function markdownToHtml(markdown) {
    if (!markdown || typeof markdown !== 'string') return '';
    let html = markdown
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    
    // Headers (must run before paragraph split)
    html = html.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.*?)$/gm, '<h1>$1</h1>');
    
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__(.*?)__/g, '<strong>$1</strong>');
    
    // Italic (avoid breaking URLs)
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    html = html.replace(/_([^_]+)_/g, '<em>$1</em>');
    
    // Unordered lists: - item or * item (then wrap consecutive <li> in <ul>)
    html = html.replace(/^[\-\*] (.*)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*?<\/li>(?:<br>\n?)*)+/g, '<ul>$&</ul>');
    
    // Numbered lists
    html = html.replace(/^\d+\. (.*)$/gm, '<li>$1</li>');
    
    // Paragraphs: double newline -> new paragraph
    html = html.replace(/\n\n+/g, '</p><p>');
    // Single newlines -> <br> so full text is visible and not collapsed
    html = html.replace(/\n/g, '<br>\n');
    
    html = '<p>' + html + '</p>';
    return html;
}

// ============================================================================
// Download Results
// ============================================================================

function downloadResults() {
    if (!window.currentResults) return;
    
    const { answer, sources, type } = window.currentResults;
    
    let content = `${type.toUpperCase()} ANALYSIS\n`;
    content += '='.repeat(50) + '\n\n';
    content += answer + '\n\n';
    content += 'SOURCES\n';
    content += '='.repeat(50) + '\n';
    sources.forEach((source, i) => {
        content += `${i + 1}. ${source.source}\n`;
    });
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `research_synthesis_${type}.txt`;
    a.click();
    URL.revokeObjectURL(url);
}

// ============================================================================
// UI Helpers
// ============================================================================

function showAnalysisSection() {
    document.getElementById('welcomeSection').style.display = 'none';
    document.getElementById('analysisSection').style.display = 'block';
}

function showMessage(element, message, type) {
    if (!element) return;
    
    element.textContent = message;
    element.className = `status-message ${type}`;
    element.style.display = 'block';
    
    if (type !== 'error') {
        setTimeout(() => {
            element.style.display = 'none';
        }, 5000);
    }
}

async function updateStats() {
    try {
        const response = await fetch(`${API_BASE}/stats`);
        const stats = await response.json();
        
        const statsSection = document.getElementById('statsSection');
        const statsBox = document.getElementById('stats');
        
        statsBox.innerHTML = `
            <p><strong>Total Vectors:</strong> ${stats.total_vectors}</p>
            <p><strong>Dimension:</strong> ${stats.embedding_dimension}</p>
            <p><strong>Total Chunks:</strong> ${stats.total_chunks}</p>
        `;
        
        statsSection.style.display = 'block';
    } catch (error) {
        console.error('Error updating stats:', error);
    }
}