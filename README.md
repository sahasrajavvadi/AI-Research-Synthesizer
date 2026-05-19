# AI Scientific Research Synthesizer 🔬

A powerful RAG (Retrieval-Augmented Generation) system that synthesizes insights across multiple research papers using Google Gemini API and FAISS vector search.

## 🎯 Features

- **PDF Upload & Processing** - Extract and chunk multiple research papers
- **Semantic Search** - Find relevant information across documents using embeddings
- **AI Synthesis** - Generate coherent answers by combining information from multiple papers
- **Research-Specific Queries** - Compare methods, identify gaps, summarize findings, analyze trends
- **Source Tracking** - See exactly which papers were cited in responses
- **Completely Free** - Uses Google Gemini free tier + local embeddings and vector store

## 🏗️ Architecture

```
User uploads PDFs
    ↓
Extract text & chunk
    ↓
Generate embeddings (SentenceTransformers)
    ↓
Store in FAISS vector database
    ↓
User asks question
    ↓
Embed question & search FAISS
    ↓
Retrieve top-k relevant chunks
    ↓
Send to Gemini API with chunks
    ↓
Get synthesized response
    ↓
Display answer + sources
```

## 🛠️ Setup Instructions

### 1. Clone/Create Project
```bash
cd research-synthesizer
```

### 2. Get Free Gemini API Key
1. Visit [Google AI Studio](https://ai.google.dev/)
2. Click "Get API key"
3. Create a new free API key
4. Copy your API key

### 3. Create .env File
```bash
cp .env.example .env
# Edit .env and paste your API key:
# GEMINI_API_KEY=your_actual_api_key_here
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

This will install:
- **streamlit** - Beautiful web UI
- **google-generativeai** - Gemini API client
- **sentence-transformers** - Local embeddings (384-dim, super fast)
- **faiss-cpu** - Vector database
- **PyPDF2** - PDF text extraction
- **python-dotenv** - Environment variable management

### 5. Run the App
```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`

## 📖 Usage Guide

### Step 1: Initialize API
- Click **Initialize API** button in the sidebar
- App will test connection to Gemini

### Step 2: Upload Research Papers
- Click **Upload PDF files** in the sidebar
- Select one or multiple PDF files
- Click **Process Documents** button
- Wait for processing (text extraction → chunking → embedding → indexing)

### Step 3: Ask Questions
Choose from:
- **General** - Regular questions across papers
- **Research Gaps** - Identify unanswered questions
- **Compare Methods** - Compare methodologies
- **Summarize** - Get comprehensive summary

### Step 4: Get Answers
- Type your question (or use quick action buttons)
- Click **Synthesize Answer**
- Get response with sources cited

## 🚀 Query Examples

### General Questions
- "What are the main findings of these papers?"
- "How do these papers relate to each other?"
- "What methodologies were used?"

### Compare Methods
- "Compare the machine learning approaches used in these papers"
- "What are the differences in data preprocessing?"
- "Which methodology is most effective?"

### Find Gaps
- "What research gaps exist?"
- "What questions remain unanswered?"
- "Where are there contradictions?"

### Summarize
- "Give me a comprehensive overview of all papers"
- "What are the common themes?"
- "What are the main conclusions?"

## 📦 Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| **LLM** | Google Gemini (free) | State-of-the-art, generous free tier |
| **Embeddings** | SentenceTransformers | Fast, local, 100% free, 384-dim |
| **Vector DB** | FAISS | Lightning fast, local, free |
| **PDF Extraction** | PyPDF2 | Simple, reliable |
| **UI** | Streamlit | Rapid development, great UX |
| **Backend** | Python | Fast to develop, easy to maintain |

## 🎯 Performance

- **Chunk Extraction**: ~1-2 seconds per 10-page PDF
- **Embedding Generation**: ~100 chunks per second
- **Vector Search**: <10ms for similarity search
- **Gemini Response**: 5-15 seconds depending on complexity

## 📁 Project Structure

```
research-synthesizer/
├── app.py              # Main Streamlit application
├── pdf_loader.py       # PDF extraction & chunking
├── embedder.py         # Text embeddings with SentenceTransformers
├── vector_store.py     # FAISS vector database
├── rag_pipeline.py     # RAG orchestration & Gemini integration
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
├── .env               # Your actual API key (create this)
└── data/              # Store vector indices (auto-created)
```

## 🔐 API Key Safety

- **Never commit .env** - It's in .gitignore
- **Use .env.example** - As template for others
- Free tier includes:
  - 60 requests per minute
  - 1,500 requests per day
  - More than enough for learning/demo

## 🎨 Advanced Features Implemented

- ✅ Multi-document RAG
- ✅ Cross-document synthesis
- ✅ Structured output formats
- ✅ Research gap identification
- ✅ Method comparison
- ✅ Source tracking
- ✅ Document statistics
- ✅ Download responses

## 💡 Customization Ideas

1. **Custom System Prompts** - Modify `RAGPipeline._build_system_prompt()`
2. **Different Models** - Change embeddings model in `embedder.py`
3. **Chunk Size Tuning** - Adjust in `pdf_loader.py`
4. **Retrieval Strategy** - Modify search params in `app.py`
5. **Output Formatting** - Customize prompts in `rag_pipeline.py`

## 🐛 Troubleshooting

### "GEMINI_API_KEY not found"
- Create `.env` file with your API key
- Run from project root directory

### "Connection failed"
- Check your internet connection
- Verify API key is correct
- Check API key hasn't exceeded daily limits

### "Out of memory with large PDFs"
- Reduce chunk size in `pdf_loader.py`
- Process fewer documents at once

### "Slow embeddings"
- First run downloads the model (slow)
- Subsequent runs are fast (cached)
- SentenceTransformers uses CPU efficiently

## 📊 Sample Use Cases

1. **Literature Review** - Quickly summarize 10+ papers
2. **Methodology Comparison** - Compare techniques across studies
3. **Finding Gaps** - Identify where research is needed
4. **Trend Analysis** - See how field has evolved
5. **Teaching** - Help students understand complex topics

## 🎓 Educational Value

Building this teaches:
- RAG systems architecture
- Vector embeddings and similarity search
- LLM prompt engineering
- PDF processing
- Vector databases (FAISS)
- Streamlit for quick prototyping
- API integration (Gemini)

## 🚀 Future Enhancements

- [ ] Chat history / conversation memory
- [ ] Citation generation (BibTeX)
- [ ] Table extraction from PDFs
- [ ] Multi-language support
- [ ] Export to formatted documents
- [ ] Web version deployment
- [ ] User accounts & document management
- [ ] Advanced filtering & search

## 📝 License

MIT - Feel free to use for personal/educational projects

## 🙏 Credits

Built using:
- Google Gemini API
- FAISS by Meta
- SentenceTransformers by Hugging Face
- Streamlit by Streamlit Inc.

---

**Happy researching! 🔬✨**

Questions? Issues? Feel free to reach out!
