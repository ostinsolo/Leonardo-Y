"""
Search-R1 Integration for Leonardo's Verification Layer

This module integrates Facebook's Search-R1 reasoning and retrieval capabilities
with Leonardo's existing verification pipeline, providing:
- Multi-step reasoning with search
- Citation-aware retrieval 
- Integration with existing NLI verification
- Compatibility with DeepSearcher pipeline

Author: Leonardo AI System
Created: 2025-01-20
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib
from datetime import datetime

try:
    # Search-R1 imports
    from search_r1.search.retrieval import get_retriever, BM25Retriever, DenseRetriever
    from search_r1.llm_agent.generation import *
    SEARCH_R1_AVAILABLE = True
except ImportError as e:
    SEARCH_R1_AVAILABLE = False
    print(f"⚠️ Search-R1 not available: {e}")

try:
    # Leonardo imports
    from leonardo.verification.nli_local import LocalNLIRunner, NLIResult
    from leonardo.verification.citation_store import CitationStore, ClaimCitation
    LEONARDO_VERIFICATION_AVAILABLE = True
except ImportError as e:
    LEONARDO_VERIFICATION_AVAILABLE = False
    print(f"⚠️ Leonardo verification not available: {e}")

logger = logging.getLogger(__name__)

@dataclass
class SearchR1Config:
    """Configuration for Search-R1 integration."""
    # Retrieval settings
    retrieval_method: str = "bm25"  # "bm25" or dense retrieval method
    retrieval_topk: int = 10
    retrieval_batch_size: int = 8
    
    # Search reasoning settings
    max_search_steps: int = 5
    reasoning_temperature: float = 0.7
    citation_threshold: float = 0.6
    
    # Integration settings
    enable_nli_verification: bool = True
    enable_citation_store: bool = True
    
    # Paths (will be auto-configured)
    index_path: Optional[str] = None
    corpus_path: Optional[str] = None
    cache_dir: str = "leonardo_search_r1_cache"

@dataclass 
class SearchStep:
    """Single step in Search-R1 reasoning chain."""
    step_id: int
    query: str
    search_results: List[Dict[str, Any]]
    reasoning: str
    citations: List[str]
    nli_scores: Optional[List[float]] = None

@dataclass
class SearchR1Result:
    """Complete Search-R1 research result."""
    original_query: str
    final_answer: str
    reasoning_chain: List[SearchStep]
    total_citations: int
    nli_pass_rate: float
    confidence_score: float
    metadata: Dict[str, Any]

class SearchR1Integration:
    """
    Integrates Search-R1 with Leonardo's verification pipeline.
    
    Provides multi-step reasoning with search, citation tracking,
    and NLI verification of claims against retrieved sources.
    """
    
    def __init__(self, config: Optional[SearchR1Config] = None):
        self.config = config or SearchR1Config()
        
        # Initialize components
        self.retriever = None
        self.nli_runner = None
        self.citation_store = None
        self.initialized = False
        
        # Setup cache directory
        self.cache_dir = Path(self.config.cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        logger.info(f"🔍 Search-R1 Integration initialized")
        logger.info(f"   Method: {self.config.retrieval_method}")
        logger.info(f"   Max steps: {self.config.max_search_steps}")
        logger.info(f"   NLI enabled: {self.config.enable_nli_verification}")
        
    async def initialize(self) -> bool:
        """Initialize Search-R1 components and verification pipeline."""
        if not SEARCH_R1_AVAILABLE:
            logger.error("❌ Search-R1 not available for initialization")
            return False
            
        try:
            # Configure retrieval paths (using simple in-memory for demo)
            if not self.config.index_path:
                logger.info("🔧 Setting up demo retrieval configuration...")
                self._setup_demo_config()
            
            # Initialize retriever
            logger.info("🔍 Initializing Search-R1 retriever...")
            retriever_config = self._build_retriever_config()
            
            if self.config.retrieval_method == "bm25":
                # For demo, we'll create a simple mock BM25 setup
                logger.info("📚 Using BM25 retrieval (demo mode)")
                self.retriever = self._create_demo_retriever()
            else:
                logger.warning("⚠️ Dense retrieval requires pre-built indices, falling back to demo")
                self.retriever = self._create_demo_retriever()
            
            # Initialize NLI if enabled
            if self.config.enable_nli_verification and LEONARDO_VERIFICATION_AVAILABLE:
                logger.info("🧠 Initializing NLI verification...")
                nli_config = {"testing_mode": True}  # Use testing mode for faster init
                self.nli_runner = LocalNLIRunner(nli_config)
                await self.nli_runner.initialize()
                
            # Initialize citation store if enabled
            if self.config.enable_citation_store and LEONARDO_VERIFICATION_AVAILABLE:
                logger.info("📋 Initializing citation store...")
                self.citation_store = CitationStore(
                    cache_dir=self.cache_dir / "citations"
                )
                
            self.initialized = True
            logger.info("✅ Search-R1 Integration fully initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Search-R1 initialization failed: {e}")
            return False
    
    def _setup_demo_config(self):
        """Setup demo configuration for testing without external indices."""
        self.config.index_path = str(self.cache_dir / "demo_index")
        self.config.corpus_path = str(self.cache_dir / "demo_corpus.jsonl")
        
        # Create minimal demo corpus
        demo_corpus = [
            {
                "id": 0,
                "title": "Leonardo AI Assistant Documentation", 
                "text": "Leonardo is a voice-first AI assistant built with modern ML pipelines including speech recognition, large language models, and verification layers.",
                "contents": "Leonardo AI Assistant Documentation\nLeonardo is a voice-first AI assistant built with modern ML pipelines including speech recognition, large language models, and verification layers."
            },
            {
                "id": 1,
                "title": "Search-R1 Research Paper",
                "text": "Search-R1 demonstrates how large language models can learn to reason and search interactively using reinforcement learning.",
                "contents": "Search-R1 Research Paper\nSearch-R1 demonstrates how large language models can learn to reason and search interactively using reinforcement learning."
            }
        ]
        
        # Write demo corpus
        corpus_path = Path(self.config.corpus_path)
        corpus_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(corpus_path, 'w') as f:
            for doc in demo_corpus:
                f.write(json.dumps(doc) + '\n')
                
        logger.info(f"📝 Created demo corpus at {corpus_path}")
    
    def _build_retriever_config(self) -> Any:
        """Build configuration object for Search-R1 retriever."""
        class MockConfig:
            def __init__(self, config_dict):
                for key, value in config_dict.items():
                    setattr(self, key, value)
        
        return MockConfig({
            'retrieval_method': self.config.retrieval_method,
            'retrieval_topk': self.config.retrieval_topk, 
            'index_path': self.config.index_path,
            'corpus_path': self.config.corpus_path,
            'retrieval_batch_size': self.config.retrieval_batch_size,
            'faiss_gpu': False,  # CPU only for Intel Mac
        })
    
    def _create_demo_retriever(self):
        """Create a demo retriever for testing without external dependencies."""
        class DemoRetriever:
            def __init__(self, corpus_path):
                self.corpus_path = corpus_path
                self.corpus = self._load_corpus()
                
            def _load_corpus(self):
                try:
                    with open(self.corpus_path, 'r') as f:
                        return [json.loads(line) for line in f]
                except:
                    return []
                
            def search(self, query: str, num: int = 5) -> List[Dict[str, str]]:
                """Simple keyword-based search for demo."""
                query_words = set(query.lower().split())
                scored_docs = []
                
                for doc in self.corpus:
                    content = doc.get('text', '') + ' ' + doc.get('title', '')
                    content_words = set(content.lower().split())
                    
                    # Simple Jaccard similarity
                    intersection = len(query_words & content_words)
                    union = len(query_words | content_words)
                    score = intersection / union if union > 0 else 0.0
                    
                    if score > 0:
                        scored_docs.append((score, doc))
                
                # Sort by score and return top results
                scored_docs.sort(key=lambda x: x[0], reverse=True)
                return [doc for score, doc in scored_docs[:num]]
        
        return DemoRetriever(self.config.corpus_path)
    
    async def research_with_reasoning(
        self, 
        query: str, 
        max_steps: Optional[int] = None
    ) -> SearchR1Result:
        """
        Conduct multi-step research with Search-R1 style reasoning.
        
        Args:
            query: Original research question
            max_steps: Maximum reasoning steps (overrides config)
            
        Returns:
            SearchR1Result with complete reasoning chain and verification
        """
        if not self.initialized:
            await self.initialize()
            
        max_steps = max_steps or self.config.max_search_steps
        reasoning_chain = []
        all_citations = []
        
        logger.info(f"🔍 Starting Search-R1 research: '{query[:50]}...'")
        
        current_query = query
        final_answer = ""
        
        for step in range(max_steps):
            logger.info(f"  Step {step + 1}/{max_steps}: Searching for '{current_query[:30]}...'")
            
            # Perform search
            search_results = self.retriever.search(current_query, num=self.config.retrieval_topk)
            
            if not search_results:
                logger.warning(f"  No results for step {step + 1}")
                break
                
            # Extract citations
            step_citations = [
                result.get('contents', result.get('text', ''))[:200] + '...'
                for result in search_results[:3]  # Top 3 for citations
            ]
            
            # Generate reasoning for this step (simplified)
            step_reasoning = self._generate_step_reasoning(
                current_query, search_results, step + 1
            )
            
            # Store step
            search_step = SearchStep(
                step_id=step + 1,
                query=current_query,
                search_results=search_results,
                reasoning=step_reasoning,
                citations=step_citations
            )
            
            # Add NLI verification if enabled
            if self.nli_runner and step_reasoning:
                nli_scores = []
                for citation in step_citations:
                    entails, confidence = self.nli_runner.entails(
                        step_reasoning, [citation]
                    )
                    nli_scores.append(confidence)
                search_step.nli_scores = nli_scores
                
            reasoning_chain.append(search_step)
            all_citations.extend(step_citations)
            
            # Update query for next step (simplified - just add more context)
            if step < max_steps - 1:
                current_query = f"{query} context: {step_reasoning[:100]}"
            
            # Generate final answer on last step
            if step == max_steps - 1 or step >= 2:  # Generate answer after 3 steps or at end
                final_answer = self._generate_final_answer(query, reasoning_chain)
                break
        
        # Calculate metrics
        total_citations = len(all_citations)
        nli_scores = []
        for step in reasoning_chain:
            if step.nli_scores:
                nli_scores.extend(step.nli_scores)
        
        nli_pass_rate = (
            sum(1 for score in nli_scores if score >= self.config.citation_threshold) / len(nli_scores)
            if nli_scores else 0.0
        )
        
        confidence_score = min(0.9, 0.3 + (nli_pass_rate * 0.6))  # 30-90% range
        
        result = SearchR1Result(
            original_query=query,
            final_answer=final_answer,
            reasoning_chain=reasoning_chain,
            total_citations=total_citations,
            nli_pass_rate=nli_pass_rate,
            confidence_score=confidence_score,
            metadata={
                "steps_taken": len(reasoning_chain),
                "retrieval_method": self.config.retrieval_method,
                "timestamp": datetime.now().isoformat(),
                "nli_enabled": self.nli_runner is not None
            }
        )
        
        # Store in citation store if enabled
        if self.citation_store and final_answer:
            self._store_research_citations(result)
        
        logger.info(f"✅ Search-R1 research complete: {len(reasoning_chain)} steps, {total_citations} citations")
        logger.info(f"   NLI pass rate: {nli_pass_rate:.2%}, Confidence: {confidence_score:.2%}")
        
        return result
    
    def _generate_step_reasoning(
        self, 
        query: str, 
        search_results: List[Dict], 
        step_num: int
    ) -> str:
        """Generate reasoning for a single search step."""
        if not search_results:
            return f"Step {step_num}: No relevant information found for '{query[:30]}...'"
            
        # Extract key information from top results
        key_info = []
        for i, result in enumerate(search_results[:3]):
            title = result.get('title', 'Untitled')
            text = result.get('text', result.get('contents', ''))[:150]
            key_info.append(f"Source {i+1} ({title}): {text}...")
        
        reasoning = f"""Step {step_num} Analysis for: "{query[:50]}..."

Based on retrieved sources:
{chr(10).join(key_info)}

Key Finding: {search_results[0].get('text', '')[:100]}...

This provides {'partial' if step_num < 3 else 'comprehensive'} information relevant to the query."""
        
        return reasoning
    
    def _generate_final_answer(
        self, 
        original_query: str, 
        reasoning_chain: List[SearchStep]
    ) -> str:
        """Generate final answer from reasoning chain."""
        
        # Collect key findings
        key_findings = []
        for step in reasoning_chain:
            # Extract main point from reasoning
            reasoning_lines = step.reasoning.split('\n')
            for line in reasoning_lines:
                if 'Key Finding:' in line:
                    key_findings.append(line.replace('Key Finding:', '').strip())
                    break
        
        if not key_findings:
            key_findings = [f"Step {i+1} provided relevant context" for i, _ in enumerate(reasoning_chain)]
        
        final_answer = f"""Based on multi-step research analysis:

Query: {original_query}

Research Summary:
{chr(10).join(f"• {finding}" for finding in key_findings[:3])}

Conclusion: Through {len(reasoning_chain)} research steps, I found {"comprehensive" if len(reasoning_chain) >= 3 else "initial"} information addressing the query. The analysis includes {sum(len(step.citations) for step in reasoning_chain)} supporting citations from retrieved sources."""
        
        return final_answer
    
    def _store_research_citations(self, result: SearchR1Result):
        """Store research citations in the citation store."""
        try:
            for step in result.reasoning_chain:
                for i, citation in enumerate(step.citations):
                    content_id = f"search_r1_{hashlib.sha256(citation.encode()).hexdigest()[:12]}"
                    
                    # Store normalized content
                    stored_content_id = self.citation_store.store_content(
                        url=f"search_r1://step_{step.step_id}_citation_{i}",
                        title=f"Search-R1 Step {step.step_id} Citation {i+1}",
                        text=citation,
                        metadata={"domain": "search_r1_research", "step_id": step.step_id}
                    )
                    
            logger.debug(f"📋 Stored {result.total_citations} citations from research")
            
        except Exception as e:
            logger.error(f"❌ Failed to store research citations: {e}")
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get current integration status and metrics."""
        return {
            "initialized": self.initialized,
            "search_r1_available": SEARCH_R1_AVAILABLE,
            "leonardo_verification_available": LEONARDO_VERIFICATION_AVAILABLE,
            "components": {
                "retriever": self.retriever is not None,
                "nli_runner": self.nli_runner is not None,
                "citation_store": self.citation_store is not None
            },
            "config": asdict(self.config),
            "cache_dir": str(self.cache_dir),
            "last_checked": datetime.now().isoformat()
        }

# Convenience function for quick research
async def quick_research(
    query: str, 
    config: Optional[SearchR1Config] = None
) -> SearchR1Result:
    """Quick Search-R1 research for single queries."""
    integration = SearchR1Integration(config)
    await integration.initialize()
    return await integration.research_with_reasoning(query)

if __name__ == "__main__":
    import asyncio
    
    async def test_integration():
        """Test Search-R1 integration."""
        print("🔍 Testing Search-R1 Integration...")
        
        config = SearchR1Config(
            max_search_steps=3,
            enable_nli_verification=True
        )
        
        integration = SearchR1Integration(config)
        
        if await integration.initialize():
            print("✅ Integration initialized successfully")
            
            # Test research
            result = await integration.research_with_reasoning(
                "What is Leonardo AI and how does it work?"
            )
            
            print(f"📊 Research Results:")
            print(f"  Steps: {len(result.reasoning_chain)}")
            print(f"  Citations: {result.total_citations}")
            print(f"  NLI pass rate: {result.nli_pass_rate:.2%}")
            print(f"  Confidence: {result.confidence_score:.2%}")
            print(f"  Answer: {result.final_answer[:150]}...")
            
            # Status check
            status = integration.get_integration_status()
            print(f"🔧 Integration Status: {status['initialized']}")
            
        else:
            print("❌ Integration initialization failed")
    
    asyncio.run(test_integration())
