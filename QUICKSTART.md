# ⚡ Quick Start Guide

Get your AI Research Synthesizer running in **5 minutes**!

## 🎯 5-Minute Setup

### Step 1: Get Free API Key (2 min)
```
1. Go to: https://ai.google.dev/
2. Click "Get API key"
3. Create a new free API key
4. Copy the key (save it somewhere)
```

### Step 2: Setup Files (1 min)
```bash
# You already have the code, just create .env file
# In: c:\Users\sahas\Downloads\airesearch\research-synthesizer\

# Create file named: .env
# Content:
GEMINI_API_KEY=your_api_key_here

# Replace "your_api_key_here" with your actual key
```

### Step 3: Install Packages (2 min)
```bash
# In PowerShell:
cd c:\Users\sahas\Downloads\airesearch\research-synthesizer
pip install -r requirements.txt
```

### Step 4: Run the App (0 min)
```bash
# Still in PowerShell:
streamlit run app.py
```

**That's it!** 🎉

The app will open at `http://localhost:8501`

---

## 🎮 First Run (Try This)

1. **Click "Initialize API"** button in sidebar
   - Should say "✅ API initialized successfully!"

2. **Upload a PDF**
   - Grab a research paper (any PDF works)
   - Upload it in sidebar

3. **Click "Process Documents"**
   - Wait for the green checkmarks
   - Should show "✅ Documents loaded and indexed"

4. **Click a Feature Button**
   - Try "📋 Comparison Table" 
   - Or "🔬 Find Research Gaps"
   - Or "📈 Trend Analysis"

5. **Download Results**
   - See the analysis
   - Click "📥 Download Response"
   - Save as text file

**Congratulations!** You've used advanced RAG! 🚀

---

## 📚 Features Available Now

### 1️⃣ Research Gap Detection 🔬
- Click button → Finds limitations in research
- Shows unanswered questions
- Lists future work directions

### 2️⃣ Comparison Table 📋
- Click button → Creates comparison table
- Shows methods, results, limitations
- Perfect for research proposals

### 3️⃣ Trend Analysis 📈
- Click button → Analyzes evolution over time
- Shows field progression
- Identifies emerging areas

### 4️⃣ Detailed Citations 🔗
- Click button → Full source tracking
- Perfect for academic writing
- Shows exactly where info comes from

### 5️⃣ General Questions ❓
- Type any question
- System synthesizes from all papers
- Shows which papers answered what

### 6️⃣ Summaries 📄
- Click "Summarize All"
- Quick overview of all papers
- Great for literature reviews

---

## 🔧 Common Issues & Fixes

### ❌ "GEMINI_API_KEY not found"
**Fix:** 
1. Make sure .env file exists
2. Make sure it has: `GEMINI_API_KEY=your_key`
3. Restart the app

### ❌ "Connection failed"
**Fix:**
1. Check internet connection
2. Verify API key is correct
3. Check you haven't exceeded daily limits (1500/day)

### ❌ "App won't start"
**Fix:**
```bash
# Try installing requirements again
pip install -r requirements.txt

# Then run app
streamlit run app.py
```

### ❌ "Slow processing"
**Fix:**
- First run is slow (downloads embeddings model)
- Subsequent runs are fast (cached)
- This is normal! ✅

---

## 📊 What Each Button Does

| Button | What It Does | Best For |
|--------|------------|----------|
| 🔬 Find Research Gaps | Identifies unanswered questions | PhD research, grant writing |
| 📊 Compare Methods | Shows methodology differences | Research proposals |
| 📄 Summarize All | Quick overview | Literature reviews |
| 📈 Trend Analysis | Field evolution & patterns | Market research |
| 📋 Comparison Table | Structured method comparison | Team presentations |
| 🔗 Detailed Citations | Full source attribution | Academic papers |
| ❓ Ask Question | Custom questions | Specific details |

---

## 💡 Pro Tips

✅ **Upload 3-5 papers first** to see system in action

✅ **Try all features** to understand capabilities

✅ **Experiment with questions** - system handles many topics

✅ **Download results** - save for your reports

✅ **Mix old & new papers** - better trend analysis

✅ **Use specific domains** - better synthesis

---

## 🎓 Example Workflows

### Workflow 1: Understand a Topic (30 min)
```
1. Find 5-10 papers on topic
2. Click "Summarize All" → Get overview
3. Click "Comparison Table" → See methods
4. Click "Find Gaps" → Identify novelty
5. Ask 2-3 custom questions → Fill details
```

### Workflow 2: Write Literature Review (1 hour)
```
1. Upload 15-20 papers on topic
2. "Summarize All" → Get structure
3. "Comparison Table" → Methods section
4. "Detailed Citations" → Full attribution
5. "Find Gaps" → Future work section
6. Download everything → Write review
```

### Workflow 3: Competitive Analysis (45 min)
```
1. Upload competitor papers
2. "Trend Analysis" → Where they're going
3. "Comparison Methods" → What they do
4. "Find Gaps" → Their weaknesses
5. Ask custom questions → Specific details
```

---

## 📈 What Makes This Powerful

✨ **Not a simple chatbot** - Actually reads ALL papers

✨ **Intelligent synthesis** - Combines insights across documents

✨ **Research-grade** - Properly cites sources

✨ **Multiple angles** - 6+ different analysis approaches

✨ **Production-ready** - Uses enterprise APIs (Gemini)

✨ **No costs** - Free tier sufficient for learning/demo

---

## 🚀 Next Steps

1. **Gather Papers** - Find 5-10 in your interest area
2. **Run Analysis** - Try all features
3. **Export Results** - Download and review
4. **Experiment** - Ask custom questions
5. **Share** - Show results to colleagues
6. **Iterate** - Upload more papers, get deeper insights

---

## ❓ Quick FAQ

**Q: How many papers can I analyze?**
A: 1-100 works great. Sweet spot is 3-20.

**Q: How long does it take?**
A: Upload to answer = 5-10 minutes for 5 papers.

**Q: Is it accurate?**
A: Yes, but always verify critical claims.

**Q: Can I share results?**
A: Yes! Download and share the text files.

**Q: What if API limits exceeded?**
A: Free tier is 1500 requests/day. Should be enough.

**Q: Can I use different papers each time?**
A: Yes! Clear and reload whenever you want.

---

## 🎯 You're Ready!

Everything is set up. Time to explore! 🚀

**Quick checklist:**
- [ ] API key obtained
- [ ] .env file created
- [ ] `pip install -r requirements.txt` run
- [ ] `streamlit run app.py` started
- [ ] "Initialize API" clicked
- [ ] A PDF uploaded
- [ ] "Process Documents" clicked
- [ ] A feature tried

**All done?** Start experimenting! 🔬✨

---

## 📚 Learn More

- Full docs: [README.md](README.md)
- Advanced features: [ADVANCED_FEATURES.md](ADVANCED_FEATURES.md)
- API docs: https://ai.google.dev/
- Streamlit docs: https://docs.streamlit.io/

---

**Happy researching!** 🔬✨
