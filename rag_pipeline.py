"""
RAG Pipeline Module
Orchestrates the Retrieval-Augmented Generation pipeline
"""

from google import genai

from typing import List, Tuple, Optional, Dict
import os
import json
from research_agent import ResearchAgent


class RAGPipeline:
    """
    Manages the complete RAG pipeline:
    1. Retrieve relevant chunks from vector store
    2. Augment prompt with retrieved chunks
    3. Generate answer using Gemini API
    """
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        print(f"[RAG_PIPELINE] Initializing with model: {model_name}")
        self.client = genai.Client(
            api_key=api_key,
            http_options={"api_version": "v1"}
        )
        self.model_name = model_name
        self.research_agent = ResearchAgent(api_key, model_name)
        print("[RAG_PIPELINE] Client initialized successfully")
        print("[RAG_PIPELINE] Research Agent initialized")

    
    def _build_system_prompt(self) -> str:
        """Build the strict RAG system prompt."""
        return """You are a STRICT document-grounded assistant.

CRITICAL RULES - NEVER VIOLATE:
1. Answer ONLY from the provided document excerpts below
2. If information is NOT in the excerpts, say: "This information is not available in the provided documents"
3. NEVER use your training knowledge
4. NEVER mention papers/documents not explicitly provided
5. NEVER infer or assume content not present
6. Each statement MUST come from the provided excerpts
7. When comparing, ONLY compare documents explicitly listed

You are operating in CLOSED-BOOK mode.
Your ONLY knowledge source is the text provided below.
"""
    
    def retrieve_and_synthesize(
        self,
        query: str,
        vector_store,
        embeddings,
        k: int = 10,
        query_type: str = "general"
    ) -> Tuple[str, List[dict]]:
        print(f"[RAG_PIPELINE] STRICT multi-doc retrieval for type={query_type}")
        
        query_embedding = embeddings.embed_text(query)
        
        # Get ALL unique uploaded documents
        unique_sources = list(set([meta['source'] for meta in vector_store.metadata]))
        
        all_results = []
        
        # Retrieve from EACH document separately
        for source in unique_sources:
            results = vector_store.search(
                query_embedding,
                k=max(2, k // len(unique_sources)),  # evenly distribute
                filter_source=source
            )
            all_results.extend(results)
        
        if not all_results:
            return "No relevant information found in the uploaded documents.", []
        
        retrieved_chunks = [result[0]["content"] for result in all_results]
        sources = [result[0]["source"] for result in all_results]
        
        augmented_prompt = self._build_augmented_prompt(
            query, retrieved_chunks, sources, query_type, unique_sources
        )
        
        answer = self._generate_with_gemini(augmented_prompt)
        
        sources_info = [
            {"source": result[0]["source"], "chunk_id": result[0]["chunk_id"]}
            for result in all_results
        ]
        
        return answer, sources_info
    
    def _build_augmented_prompt(
        self,
        query: str,
        chunks: List[str],
        sources: List[str],
        query_type: str,
        unique_sources: List[str] = None
    ) -> str:
        """
        Build the prompt augmented with retrieved chunks.
        
        Args:
            query: User's question
            chunks: Retrieved text chunks
            sources: Source document names
            query_type: Type of query for specialized prompts
            unique_sources: List of unique source documents
            
        Returns:
            Augmented prompt string
        """
        if unique_sources is None:
            unique_sources = list(set(sources))
        
        source_list = ", ".join(unique_sources)
        chunks_text = "\n\n".join(
            [f"[From {source}]\n{chunk}" for chunk, source in zip(chunks, sources)]
        )
        
        source_constraint = f"""AVAILABLE DOCUMENTS (ONLY SOURCE OF TRUTH):
{source_list}

You MUST ONLY discuss these documents.
Do NOT mention any other papers, research, or documents.
If a document is not in the list above, you CANNOT discuss it.

"""
        
        if query_type == "gaps":
            prompt_template = """Using ONLY the following research excerpts, identify and discuss research gaps.
Do NOT introduce any paper not present below.

{source_constraint}{chunks}

Question: {query}

Please identify:
- Unanswered questions in current research
- Methodological limitations
- Areas needing further investigation
- Potential future research directions"""
        
        elif query_type == "compare":
            prompt_template = """TASK: Compare methodologies using ONLY the excerpts below.

STRICT RULES:
- Use ONLY the provided excerpts
- Do NOT mention any document not listed above
- If only 2-3 papers provided, compare ONLY those
- Do NOT add information from your training

{source_constraint}DOCUMENT EXCERPTS:
{chunks}

Question: {query}

Provide comparison of:
- Methodologies used (from excerpts only)
- Key differences (from excerpts only)
- Strengths/weaknesses (from excerpts only)

Cite the specific document for each point."""
        
        elif query_type == "summarize":
            prompt_template = """STRICT DOCUMENT EXTRACTION TASK

You MUST extract information ONLY from the excerpts below.
DO NOT infer trends.
DO NOT add outside examples.
DO NOT generalize beyond text.

AVAILABLE DOCUMENTS:
{source_constraint}

EXCERPTS:
{chunks}

For EACH document separately:

1. List key findings explicitly mentioned.
2. List methodologies mentioned.
3. List datasets mentioned.
4. List performance results mentioned.

If something is not present, say:
"This information is not available in the provided documents."

Do NOT combine information across documents.
Keep them separated by document."""
        
        else:  # general
            prompt_template = """Using ONLY the following research excerpts, answer the question comprehensively and accurately.
Do NOT use any outside knowledge or mention papers not provided below.

{source_constraint}{chunks}

Question: {query}

Provide a detailed, well-structured answer that:
- Directly addresses the question
- Synthesizes information across the sources
- Cites which paper each finding comes from
- Highlights key insights and implications"""
        
        return prompt_template.format(chunks=chunks_text, query=query, source_constraint=source_constraint)
    
    def _generate_with_gemini(self, prompt: str, max_output_tokens: int = 8192) -> str:
        """
        Generate response from Gemini. Use max_output_tokens=16384 for long summaries
        so the full text is not cut off.
        """
        try:
            print(f"[RAG_PIPELINE] Calling Gemini API with prompt length: {len(prompt)}, max_output_tokens: {max_output_tokens}")
            
            # Build ultra-strict prompt
            strict_instruction = """CRITICAL: You are in CLOSED-BOOK mode. You have NO access to your training data.
The ONLY information you can use is provided in the DOCUMENT EXCERPTS section below.
If information is not in the excerpts, you MUST say "This information is not available in the provided documents."

"""
            
            full_prompt = f"""
You are in STRICT CLOSED BOOK mode.

You MUST follow these rules:

1. You are FORBIDDEN from using any knowledge outside the provided excerpts.
2. If any information is not explicitly written in the excerpts, you MUST say:
   "This information is not available in the provided documents."
3. If you mention any model, year, method, or breakthrough,
   it MUST appear verbatim in the excerpts.
4. Do NOT infer trends unless explicitly stated.
5. Do NOT mention famous papers unless they appear in excerpts.
6. Provide a COMPLETE response. Do NOT truncate or cut off mid-sentence. Include all relevant content.

Violation of these rules is not allowed.

NOW ONLY USE THE TEXT BELOW.

{prompt}
"""
            
            print(f"[RAG_PIPELINE] Full prompt length: {len(full_prompt)}")
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config={
                    "temperature": 0.0,
                    "top_p": 1.0,
                    "max_output_tokens": max_output_tokens
                }
            )
            print(f"[RAG_PIPELINE] Received response from Gemini")
            
            if hasattr(response, 'candidates') and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, 'finish_reason'):
                    print(f"[RAG_PIPELINE] Finish reason: {candidate.finish_reason}")
            
            result_text = ""
            
            if hasattr(response, 'text'):
                result_text = str(response.text)
                print(f"[RAG_PIPELINE] Got text directly: {len(result_text)} chars")
            elif hasattr(response, 'candidates') and len(response.candidates) > 0:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content'):
                    if hasattr(candidate.content, 'parts') and len(candidate.content.parts) > 0:
                        result_text = str(candidate.content.parts[0].text)
                        print(f"[RAG_PIPELINE] Got text from parts: {len(result_text)} chars")
            
            if result_text:
                print(f"[RAG_PIPELINE] Final response length: {len(result_text)} characters")
                return result_text
            
            print("[RAG_PIPELINE] ERROR: Could not extract text from response")
            return "Unable to generate response from API"
            
        except Exception as e:
            print(f"[RAG_PIPELINE] Gemini API Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"Error generating response: {str(e)}"

    
    def test_connection(self) -> bool:
        try:
            print("[RAG_PIPELINE] Testing connection to Gemini API")
            response = self.client.models.generate_content(
                model=self.model_name,
                contents="Say OK"
            )
            print("[RAG_PIPELINE] Connection test successful")
            return True
        except Exception as e:
            print(f"[RAG_PIPELINE] Connection test failed: {str(e)}")
            return False

    def analyze_query(self, query: str, num_documents: int = 1) -> dict:
        """
        Analyze user question to detect intent and whether to use all documents.
        Returns: {"intent": "summarize_all"|"compare"|"gaps"|"trends"|"table"|"citations"|"general", "use_all_documents": bool}
        """
        if not query or not query.strip():
            return {"intent": "general", "use_all_documents": True}
        prompt = f"""You are a query classifier for a RAG system. The user has uploaded {num_documents} document(s).

User question: "{query.strip()}"

Classify the intent into EXACTLY one of these labels:
- summarize_all: user wants a summary of all documents (e.g. "summarize them", "summarize all 3 documents", "give me a summary of everything")
- compare: user wants to compare methodologies/approaches across documents
- gaps: user wants research gaps, limitations, or future work
- trends: user wants trends, evolution, or timeline analysis
- table: user wants a comparison table
- citations: user wants detailed citations or exact quotes from documents
- general: specific factual question or other

Also decide: use_all_documents = true if the user clearly wants information from ALL documents (e.g. "all documents", "all 3", "each document", "summarize them", "across the papers"). Otherwise false.

Respond with ONLY a JSON object, no other text, in this exact format:
{{"intent": "<one of the labels above>", "use_all_documents": true or false}}"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={"temperature": 0.0, "max_output_tokens": 128}
            )
            text = getattr(response, "text", None) or ""
            if not text and hasattr(response, "candidates") and response.candidates:
                part = response.candidates[0].content.parts[0]
                text = getattr(part, "text", "") or ""
            text = text.strip().replace("```json", "").replace("```", "").strip()
            out = json.loads(text)
            intent = out.get("intent", "general")
            if intent not in ("summarize_all", "compare", "gaps", "trends", "table", "citations", "general"):
                intent = "general"
            use_all = bool(out.get("use_all_documents", num_documents > 1))
            if intent == "summarize_all":
                use_all = True
            print(f"[RAG_PIPELINE] analyze_query -> intent={intent}, use_all_documents={use_all}")
            return {"intent": intent, "use_all_documents": use_all}
        except Exception as e:
            print(f"[RAG_PIPELINE] analyze_query failed: {e}, defaulting to general + use_all")
            return {"intent": "general", "use_all_documents": num_documents > 1}

    def ask(
        self,
        query: str,
        vector_store,
        embeddings,
        k: int = 12,
        query_type_override: Optional[str] = None,
    ) -> Tuple[str, List[dict]]:
        """
        Single RAG entry point: analyze the question, then retrieve from documents and synthesize.
        If query_type_override is set (e.g. 'summarize', 'gaps'), use it; otherwise analyze_query().
        """
        unique_sources = list(set([meta["source"] for meta in vector_store.metadata]))
        num_docs = len(unique_sources)

        if query_type_override and query_type_override in (
            "gaps", "table", "summarize", "trends", "citations", "compare", "general"
        ):
            intent = "summarize_all" if query_type_override == "summarize" else query_type_override
            use_all = intent in ("summarize_all", "table", "gaps", "trends", "citations") or num_docs <= 1
        else:
            analyzed = self.analyze_query(query or "Summarize all documents.", num_documents=num_docs)
            intent = analyzed["intent"]
            use_all = analyzed["use_all_documents"]

        # Map frontend type names to pipeline methods
        if intent == "summarize_all":
            return self.summarize_all_documents(
                vector_store=vector_store, embeddings=embeddings, k=k
            )
        if intent == "gaps":
            return self.identify_research_gaps(
                vector_store=vector_store, embeddings=embeddings, k=k
            )
        if intent == "table":
            return self.generate_comparison_table(
                vector_store=vector_store, embeddings=embeddings, k=k
            )
        if intent == "trends":
            return self.analyze_trends(
                vector_store=vector_store, embeddings=embeddings, k=k
            )
        if intent == "citations":
            return self.generate_detailed_citations(
                query=query or "What are the key findings?",
                vector_store=vector_store,
                embeddings=embeddings,
                k=k,
            )
        # compare or general: use retrieve_and_synthesize (always pulls from all docs when multiple)
        return self.retrieve_and_synthesize(
            query=query or "Summarize the main points.",
            vector_store=vector_store,
            embeddings=embeddings,
            k=k,
            query_type="compare" if intent == "compare" else "general",
        )

    
    def identify_research_gaps(
        self,
        vector_store,
        embeddings,
        k: int = 6
    ) -> Tuple[str, List[dict]]:
        """
        Identify research gaps, limitations, and open problems.
        
        Args:
            vector_store: FAISSVectorStore instance
            embeddings: EmbeddingEngine instance
            k: Number of chunks to retrieve
            
        Returns:
            Tuple of (gaps_analysis, sources_used)
        """
        print(f"[RAG_PIPELINE] identify_research_gaps called with k={k}")
        gap_query = "limitations future work open problems research gaps unanswered questions"
        query_embedding = embeddings.embed_text(gap_query)
        unique_sources = list(set([meta['source'] for meta in vector_store.metadata]))
        
        all_results = []
        k_per_doc = max(3, k)
        for source in unique_sources:
            results = vector_store.search(
                query_embedding,
                k=k_per_doc,
                filter_source=source
            )
            all_results.extend(results)
        
        search_results = all_results
        
        if len(search_results) == 0:
            return "No gap-related information found.", []
        
        retrieved_chunks = [result[0]["content"] for result in search_results]
        sources = [result[0]["source"] for result in search_results]
        unique_sources_list = list(set(sources))
        source_list = ", ".join(unique_sources_list)
        print(f"[RAG_PIPELINE] Retrieved sources: {unique_sources_list}")
        
        prompt = f"""STRICT EXTRACTION TASK

You MUST extract ONLY sentences that explicitly contain:
- the word "limitation"
- the phrase "future work"
- the phrase "open problem"
- the phrase "research gap"
- the word "challenge"

If such phrases do NOT appear, say:
"This information is not available in the provided documents."

AVAILABLE DOCUMENTS:
{source_list}

DOCUMENT EXCERPTS:
{"\n\n".join([f"[From {source}]\n{chunk}" for chunk, source in zip(retrieved_chunks, sources)])}

Extract the sentences exactly as written.
Do NOT paraphrase.
Do NOT interpret.
Do NOT generalize.
"""
        
        answer = self._generate_with_gemini(prompt)
        
        sources_info = [
            {"source": result[0]["source"], "chunk_id": result[0]["chunk_id"]}
            for result in search_results
        ]
        
        return answer, sources_info
    
    def summarize_all_documents(
        self,
        vector_store,
        embeddings,
        k: int = 12
    ) -> Tuple[str, List[dict]]:
        """
        Summarize all uploaded documents using Map-Reduce.
        Uses more chunks per doc (k) and higher output token limit so full text is not cut off.
        
        Args:
            vector_store: FAISSVectorStore instance
            embeddings: EmbeddingEngine instance
            k: Number of chunks per document (default 12 for full coverage)
            
        Returns:
            Tuple of (summary, sources_used)
        """
        print(f"[RAG_PIPELINE] summarize_all_documents called with k={k}")
        
        unique_sources = list(set([meta['source'] for meta in vector_store.metadata]))
        print(f"[RAG_PIPELINE] Found {len(unique_sources)} unique documents: {unique_sources}")
        
        all_summaries = []
        all_sources_info = []
        
        # Map: Summarize each document individually
        for source_file in unique_sources:
            print(f"[RAG_PIPELINE] Summarizing: {source_file}")
            
            search_results = vector_store.search(
                embeddings.embed_text("main findings methodology results conclusions"),
                k=k,
                filter_source=source_file
            )
            
            if not search_results:
                continue
            
            chunks = [res[0]["content"] for res in search_results]
            all_sources_info.extend([{"source": res[0]["source"], "chunk_id": res[0]["chunk_id"]} for res in search_results])
            
            map_prompt = f"""Using ONLY the excerpts from '{source_file}', provide a concise summary.

EXCERPTS:
{" ".join(chunks)}

Summarize:
- Main research question/objective
- Methodology used
- Key findings/results
- Main conclusions

Keep it brief and factual."""
            
            summary = self._generate_with_gemini(map_prompt)
            all_summaries.append(f"### {source_file}\n{summary}")
        
        # Reduce: Combine all summaries
        print(f"[RAG_PIPELINE] Combining {len(all_summaries)} summaries")
        final_prompt = f"""Combine the following document summaries into one cohesive overview.

DOCUMENT SUMMARIES:
{"\n\n".join(all_summaries)}

Create a unified summary that:
- Lists each document and its key contributions
- Highlights common themes across documents
- Notes any unique findings
- Keeps each document's summary separate and clear

Format with clear document headings."""
        
        final_summary = self._generate_with_gemini(final_prompt, max_output_tokens=16384)
        
        return final_summary, all_sources_info
    
    def generate_comparison_table(
        self,
        vector_store,
        embeddings,
        k: int = 5,
        status_callback=None
    ) -> Tuple[str, List[dict]]:
        """
        Map-Reduce approach: Query each paper individually, then merge.
        """
        print(f"[RAG_PIPELINE] generate_comparison_table called with k={k} (Map-Reduce)")
        
        unique_sources = list(set([meta['source'] for meta in vector_store.metadata]))
        print(f"[RAG_PIPELINE] Found {len(unique_sources)} unique documents: {unique_sources}")
        
        all_paper_summaries = []
        all_sources_info = []
        total_papers = len(unique_sources)
        
        for i, source_file in enumerate(unique_sources):
            if status_callback:
                progress = i / total_papers
                status_callback(progress, f"Analyzing: {source_file} ({i+1}/{total_papers})")
            
            print(f"[RAG_PIPELINE] Mapping paper {i+1}/{total_papers}: {source_file}")
            
            search_results = vector_store.search(
                embeddings.embed_text("methodology results dataset metrics"), 
                k=k, 
                filter_source=source_file
            )
            
            if not search_results:
                print(f"[RAG_PIPELINE] No results for {source_file}, skipping")
                continue
                
            chunks = [res[0]["content"] for res in search_results]
            all_sources_info.extend([{"source": res[0]["source"], "chunk_id": res[0]["chunk_id"]} for res in search_results])
            
            map_prompt = f"""Using ONLY the excerpts from the document '{source_file}', extract:
- Main Methodology/Model architecture
- Dataset details (size, languages, source)
- Key Performance Results (accuracy, metrics)

Keep it to concise bullet points.

EXCERPTS:
{" ".join(chunks)}"""
            
            print(f"[RAG_PIPELINE] Generating summary for {source_file}")
            summary = self._generate_with_gemini(map_prompt)
            all_paper_summaries.append(f"### DOCUMENT: {source_file}\n{summary}")

        if status_callback:
            status_callback(0.9, "Merging all insights into final table...")
        
        print(f"[RAG_PIPELINE] REDUCE phase: Combining {len(all_paper_summaries)} summaries")
        final_reduce_prompt = f"""TASK: Using the individual summaries below, create one unified Markdown comparison table.

| Document | Method | Dataset | Key Results |
|:---|:---|:---|:---|

IMPORTANT: Complete ALL rows for all {len(unique_sources)} documents.

SUMMARIES:
{" ".join(all_paper_summaries)}

Create the complete table now. Provide the FULL table; do not truncate."""
        
        final_table = self._generate_with_gemini(final_reduce_prompt, max_output_tokens=8192)
        
        if status_callback:
            status_callback(1.0, "Analysis Complete!")
        
        return final_table, all_sources_info
    
    def analyze_trends(
        self,
        vector_store,
        embeddings,
        k: int = 6
    ) -> Tuple[str, List[dict]]:
        """
        Analyze trends and evolution across papers over time.
        
        Args:
            vector_store: FAISSVectorStore instance
            embeddings: EmbeddingEngine instance
            k: Number of chunks to retrieve
            
        Returns:
            Tuple of (trend_analysis, sources_used)
        """
        print(f"[RAG_PIPELINE] analyze_trends called with k={k}")
        trend_query = "year date timeline evolution progress improvement advancement innovation breakthrough discovery"
        query_embedding = embeddings.embed_text(trend_query)
        
        # Get all unique documents
        unique_sources = list(set([meta['source'] for meta in vector_store.metadata]))
        
        all_results = []
        k_per_doc = max(3, k)
        for source in unique_sources:
            results = vector_store.search(
                query_embedding,
                k=k_per_doc,
                filter_source=source
            )
            all_results.extend(results)
        
        search_results = all_results
        
        if len(search_results) == 0:
            return "No temporal/trend information found.", []
        
        retrieved_chunks = [result[0]["content"] for result in search_results]
        sources = [result[0]["source"] for result in search_results]
        unique_sources_list = list(set(sources))
        source_list = ", ".join(unique_sources_list)
        print(f"[RAG_PIPELINE] Retrieved sources: {unique_sources_list}")
        
        prompt = f"""Using ONLY the following research excerpts, analyze trends and evolution.
Do NOT introduce any paper not present below.

The available papers are: {source_list}
You MUST only discuss these papers.

{"\n\n".join([f"[From {source}]\n{chunk}" for chunk, source in zip(retrieved_chunks, sources)])}

Analyze and synthesize the following:

📈 **TIMELINE OF PROGRESS**
- How has the field evolved from earliest to latest papers?
- What major breakthroughs occurred?
- What methodologies were replaced by newer ones?
- Show chronological progression if possible

🔄 **SHIFTS IN METHODOLOGY**
- What changed in how research is conducted?
- What tools or approaches became standard?
- What older approaches were abandoned?
- Why did these changes happen?

📊 **PERFORMANCE/RESULTS TRENDS**
- Have results improved over time?
- What metrics show the most improvement?
- Are there diminishing returns?
- What's the trajectory?

💡 **EMERGING TRENDS & PATTERNS**
- What new areas are being explored?
- What's becoming more/less popular?
- What are researchers focusing on now?
- What future directions are suggested?

🎯 **KEY INSIGHTS**
- What's the most important trend?
- Where is the field heading?
- What can we predict about future research?
- What opportunities exist for new research?"""
        
        answer = self._generate_with_gemini(prompt)
        
        sources_info = [
            {"source": result[0]["source"], "chunk_id": result[0]["chunk_id"]}
            for result in search_results
        ]
        
        return answer, sources_info
    
    def generate_detailed_citations(
        self,
        query: str,
        vector_store,
        embeddings,
        k: int = 6
    ) -> Tuple[str, List[dict]]:
        """
        Generate response with detailed citation tracking.
        
        Args:
            query: User's question
            vector_store: FAISSVectorStore instance
            embeddings: EmbeddingEngine instance
            k: Number of chunks to retrieve
            
        Returns:
            Tuple of (response_with_citations, detailed_sources)
        """
        print(f"[RAG_PIPELINE] generate_detailed_citations called with query: '{query[:50]}...', k={k}")
        query_embedding = embeddings.embed_text(query)
        
        # Get all unique documents
        unique_sources = list(set([meta['source'] for meta in vector_store.metadata]))
        
        all_results = []
        k_per_doc = max(3, k)
        for source in unique_sources:
            results = vector_store.search(
                query_embedding,
                k=k_per_doc,
                filter_source=source
            )
            all_results.extend(results)
        
        search_results = all_results
        
        if len(search_results) == 0:
            return "No relevant information found.", []
        
        retrieved_chunks = [result[0]["content"] for result in search_results]
        sources = [result[0]["source"] for result in search_results]
        unique_sources_list = list(set(sources))
        source_list = ", ".join(unique_sources_list)
        num_docs_citations = len(unique_sources_list)
        print(f"[RAG_PIPELINE] Retrieved sources: {unique_sources_list}")
        
        prompt = f"""MANDATORY EXTRACTION TASK

You MUST extract sentences from ALL {num_docs_citations} documents listed below.

AVAILABLE DOCUMENTS (YOU MUST USE ALL OF THEM):
{source_list}

DOCUMENT EXCERPTS:
{"\n\n".join([f"[EXCERPT {i+1} from {source}]\n{chunk}" for i, (chunk, source) in enumerate(zip(retrieved_chunks, sources))])}

Question: {query}

MANDATORY INSTRUCTIONS:
1. You MUST extract sentences from EACH of the {num_docs_citations} documents
2. Start with: "From [document name]: [exact sentence]"
3. Do this for ALL {num_docs_citations} documents
4. If a document has no relevant information, say: "From [document name]: No relevant information found in excerpts"
5. Do NOT skip any document
6. Do NOT paraphrase - copy exact sentences

Format:
From 2001.00139v1.pdf:
- [exact sentence from excerpt]

From 2308.13418v1.pdf:
- [exact sentence from excerpt]

From 2407.04577v2.pdf:
- [exact sentence from excerpt]

You MUST include ALL {num_docs_citations} documents in your response. Provide a COMPLETE response; do not truncate."""

        answer = self._generate_with_gemini(prompt, max_output_tokens=8192)
        
        detailed_sources = [
            {
                "source": result[0]["source"],
                "chunk_id": result[0]["chunk_id"],
                "relevance_score": float(result[1])
            }
            for result in search_results
        ]
        
        return answer, detailed_sources
    
    # ═════════════════════════════════════════════════════════════════════════════
    # 🤖 RESEARCH AGENT METHODS - Automatic Research Component Extraction
    # ═════════════════════════════════════════════════════════════════════════════
    
    def extract_research_components(
        self,
        vector_store,
        embeddings,
        k: int = 8
    ) -> Dict[str, Dict[str, str]]:
        """
        Use Research Agent to extract all components from uploaded papers.
        
        Args:
            vector_store: FAISSVectorStore instance
            embeddings: EmbeddingEngine instance
            k: Number of chunks per document
            
        Returns:
            Dictionary: {document_name: {component: extraction}}
        """
        print("🤖 [RESEARCH_AGENT] Starting automatic research component extraction...")
        
        unique_sources = list(set([meta['source'] for meta in vector_store.metadata]))
        all_extractions = {}
        
        for source in unique_sources:
            print(f"📄 Processing: {source}")
            
            # Get representative chunks from this document
            search_results = vector_store.search(
                embeddings.embed_text("research methodology findings datasets challenges limitations"),
                k=k,
                filter_source=source
            )
            
            if not search_results:
                continue
            
            chunks = [res[0]["content"] for res in search_results]
            
            # Use research agent to extract components
            components = self.research_agent.extract_all_components(chunks, source)
            all_extractions[source] = components
        
        print("✅ Research component extraction complete!")
        return all_extractions
    
    def compare_research_components(
        self,
        all_papers_analysis: Dict[str, Dict[str, str]],
        component: str
    ) -> str:
        """
        Compare a specific component across all papers using Research Agent.
        
        Args:
            all_papers_analysis: Dictionary from extract_research_components()
            component: Which component to compare (problem, methodology, findings, etc.)
            
        Returns:
            Comparison analysis
        """
        return self.research_agent.compare_papers(all_papers_analysis, component)
    
    def identify_research_frontiers(
        self,
        all_papers_analysis: Dict[str, Dict[str, str]]
    ) -> Dict[str, str]:
        """
        Use Research Agent to identify emerging research frontiers.
        
        Args:
            all_papers_analysis: Dictionary from extract_research_components()
            
        Returns:
            Dictionary with frontier analysis
        """
        papers_list = list(all_papers_analysis.values())
        return self.research_agent.identify_research_frontiers(papers_list)
    
    def generate_comprehensive_research_summary(
        self,
        all_papers_analysis: Dict[str, Dict[str, str]],
        focus_area: str = "contributions"
    ) -> str:
        """
        Generate comprehensive research summary using Research Agent.
        
        Args:
            all_papers_analysis: Dictionary from extract_research_components()
            focus_area: Which component to focus on
            
        Returns:
            Comprehensive synthesis
        """
        papers_list = list(all_papers_analysis.values())
        return self.research_agent.generate_research_summary(papers_list, focus_area)