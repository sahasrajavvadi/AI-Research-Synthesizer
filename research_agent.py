"""
Research Paper AI Agent
Automatically extracts key research components from papers using structured prompts
"""

from google import genai
from typing import Dict, List, Tuple, Optional
import json
import os


class ResearchAgent:
    """
    An intelligent agent that extracts key research components from papers:
    - Problem Statement
    - Research Methodology
    - Dataset Information
    - Key Findings
    - Research Gaps
    - Limitations
    - Future Work
    - Key Contributions
    """
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        self.client = genai.Client(
            api_key=api_key,
            http_options={"api_version": "v1"}
        )
        self.model_name = model_name
        self.extraction_prompts = self._build_extraction_prompts()
    
    def _build_extraction_prompts(self) -> Dict[str, str]:
        """Build specialized prompts for each research component."""
        return {
            "problem": """You are a research analyst extracting the PROBLEM STATEMENT.
From the provided paper excerpt, extract:
1. What problem does this paper address?
2. Why is it important?
3. What limitations did previous work have?

Format as bullet points. Be concise but specific. Extract ONLY what's stated in the text.""",

            "methodology": """You are a research analyst extracting the METHODOLOGY.
From the provided paper excerpt, extract:
1. What methods/algorithms are proposed?
2. What is the technical approach?
3. What are the key steps in the process?
4. Any novel techniques introduced?

Format as bullet points with technical details.""",

            "dataset": """You are a research analyst extracting DATASET INFORMATION.
From the provided paper excerpt, extract:
1. What datasets are used?
2. Dataset size/scale information
3. How was data collected?
4. Any preprocessing or preparation steps?
5. Dataset characteristics (language, domain, etc.)

If no dataset mentioned, state: "No specific dataset information provided".""",

            "findings": """You are a research analyst extracting KEY FINDINGS.
From the provided paper excerpt, extract:
1. What are the main results?
2. Performance metrics or improvements achieved
3. Comparison with baseline/previous work
4. Surprising or notable discoveries

Format as bullet points with specific numbers/results where available.""",

            "gaps": """You are a research analyst identifying RESEARCH GAPS.
From the provided paper excerpt, identify:
1. What does the paper NOT address?
2. What limitations are mentioned?
3. What questions remain unanswered?
4. What future work is suggested?
5. What's missing from previous research?

Be critical and analytical. Infer gaps from the paper's scope.""",

            "limitations": """You are a research analyst extracting LIMITATIONS.
From the provided paper excerpt, extract:
1. Explicit limitations mentioned by authors
2. Scope limitations
3. Scalability issues
4. Applicability constraints
5. Assumptions made

Format as candid bullet points.""",

            "future": """You are a research analyst extracting FUTURE WORK.
From the provided paper excerpt, extract:
1. What future research is proposed?
2. How can this work be extended?
3. What new directions are suggested?
4. Dependencies on other work

Extract ONLY explicitly stated future work. Be specific.""",

            "contributions": """You are a research analyst extracting KEY CONTRIBUTIONS.
From the provided paper excerpt, extract:
1. Main scientific contributions
2. Novel methods or approaches
3. Achievements or breakthroughs
4. Practical contributions

List 3-5 significant contributions with clear descriptions."""
        }
    
    def extract_all_components(
        self,
        chunks: List[str],
        source: str
    ) -> Dict[str, str]:
        """
        Extract all research components from paper chunks.
        
        Args:
            chunks: List of text chunks from paper
            source: Source document name
            
        Returns:
            Dictionary with extracted components
        """
        print(f"🔬 [RESEARCH_AGENT] Analyzing '{source}'...")
        
        combined_text = "\n".join(chunks)
        results = {}
        
        for component, prompt in self.extraction_prompts.items():
            print(f"  ├─ Extracting {component}...")
            try:
                extraction = self._extract_component(combined_text, prompt)
                results[component] = extraction
            except Exception as e:
                results[component] = f"⚠ Extraction error: {str(e)}"
        
        print(f"  └─ ✅ Analysis complete for '{source}'\n")
        return results
    
    def _extract_component(self, text: str, prompt: str) -> str:
        """Extract a single component using the LLM."""
        augmented_prompt = f"""{prompt}

===== PAPER EXCERPT =====
{text}

===== ANALYSIS =====
Analyze the above text and extract the requested information."""
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=augmented_prompt,
            config={
                "temperature": 0.3,
                "top_p": 0.9,
                "top_k": 40,
                "max_output_tokens": 1000
            }
        )
        
        return response.text if response.text else "No information extracted."
    
    def compare_papers(
        self,
        papers_data: Dict[str, Dict[str, str]],
        component: str
    ) -> str:
        """
        Compare the same component across multiple papers.
        
        Args:
            papers_data: Dict with paper names and their extracted components
            component: Component to compare (e.g., 'methodology', 'findings')
            
        Returns:
            Comparison analysis
        """
        print(f"📊 [RESEARCH_AGENT] Comparing {component} across papers...")
        
        comparison_data = {}
        for paper, components in papers_data.items():
            if component in components:
                comparison_data[paper] = components[component]
        
        if not comparison_data:
            return f"No '{component}' data available for comparison."
        
        prompt = f"""You are a research analyst comparing research papers.

Component to compare: {component}

Paper extractions:
"""
        for paper, content in comparison_data.items():
            prompt += f"\n{paper}:\n{content}\n"
        
        prompt += f"""
=== COMPARISON ANALYSIS ===
1. Similarities across papers
2. Key differences
3. Complementary approaches
4. What each paper does best
5. Overall research landscape for this component

Provide a structured comparison analysis."""
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={
                "temperature": 0.4,
                "top_p": 0.9,
                "max_output_tokens": 1500
            }
        )
        
        return response.text if response.text else "Comparison generation failed."
    
    def identify_research_frontiers(
        self,
        all_papers_analysis: List[Dict[str, str]]
    ) -> Dict[str, str]:
        """
        Analyze papers to identify research frontiers and trends.
        
        Args:
            all_papers_analysis: List of extracted components from all papers
            
        Returns:
            Dictionary with frontier analysis
        """
        print("🚀 [RESEARCH_AGENT] Identifying research frontiers...")
        
        gaps_text = "\n---\n".join([
            f"Paper: {i+1}\n{paper.get('gaps', 'No gaps identified')}"
            for i, paper in enumerate(all_papers_analysis)
        ])
        
        prompt = f"""You are a research strategist analyzing research gaps across multiple papers.

RESEARCH GAPS ACROSS ALL PAPERS:
{gaps_text}

=== RESEARCH FRONTIER ANALYSIS ===

Identify and analyze:
1. Common research gaps (gaps that appear in multiple papers)
2. Emerging research frontiers (new areas suggested by multiple papers)
3. Critical missing pieces (what the field needs most)
4. Interdisciplinary opportunities (connections between different gaps)
5. High-impact research directions (gaps that could transform the field)

Format as prioritized bullet points with impact assessment."""
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={
                "temperature": 0.5,
                "top_p": 0.9,
                "max_output_tokens": 2000
            }
        )
        
        analysis = response.text if response.text else "Frontier analysis failed."
        
        return {
            "frontiers": analysis,
            "papers_analyzed": len(all_papers_analysis),
            "synthesis_type": "research_frontiers"
        }
    
    def generate_research_summary(
        self,
        all_papers_analysis: List[Dict[str, str]],
        focus_area: str = "contributions"
    ) -> str:
        """
        Generate a comprehensive research summary across papers.
        
        Args:
            all_papers_analysis: Extracted components from all papers
            focus_area: Which component to focus on
            
        Returns:
            Comprehensive summary
        """
        print(f"📝 [RESEARCH_AGENT] Generating research summary (focus: {focus_area})...")
        
        summaries = []
        for i, paper in enumerate(all_papers_analysis):
            if focus_area in paper:
                summaries.append(f"Paper {i+1}:\n{paper[focus_area]}")
        
        combined_summaries = "\n---\n".join(summaries)
        
        prompt = f"""You are a research summarist. Synthesize key information from multiple papers.

EXTRACTED {focus_area.upper()} FROM ALL PAPERS:
{combined_summaries}

=== SYNTHESIS ===

Create a comprehensive summary that:
1. Identifies common themes
2. Highlights unique contributions
3. Shows progression of research
4. Identifies patterns and trends
5. Suggests the overall research narrative

Be insightful and analytical. This is for a research overview document."""
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config={
                "temperature": 0.4,
                "top_p": 0.9,
                "max_output_tokens": 2000
            }
        )
        
        return response.text if response.text else "Summary generation failed."
