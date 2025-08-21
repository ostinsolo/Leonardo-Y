"""
Real NLI Verification Test - Production Models
Tests actual HuggingFace NLI models without mocking

Uses:
- typeform/distilbert-base-uncased-mnli (67M params, fast)
- MoritzLaurer/DeBERTa-v3-base-mnli (184M params, 90% accuracy)

This test will download models and perform real entailment checking.
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

# Add leonardo package to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from leonardo.verification.nli_local import LocalNLIRunner
from leonardo.verification.citation_store import CitationStore, ContentSpan
from leonardo.verification.research_verifier import ResearchVerifier

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RealNLITestSuite:
    """Production NLI testing with real HuggingFace models."""
    
    def __init__(self):
        self.test_results = {
            "nli_model_loading": False,
            "basic_entailment": False,
            "claim_verification": False,
            "citation_integration": False,
            "research_verifier": False
        }
        
        # Test cases for NLI verification
        self.test_cases = [
            # Positive entailment cases
            ("The weather is sunny today", "Today's forecast shows clear skies and sunshine", True),
            ("The system is working properly", "All components are functioning correctly", True),
            ("Python is a programming language", "Python is used for software development", True),
            
            # Negative entailment cases  
            ("It is raining heavily", "The weather is sunny and clear", False),
            ("The server is down", "All systems are operational", False),
            ("The meeting is at 3 PM", "The meeting is scheduled for 9 AM", False),
            
            # Neutral cases (should not entail)
            ("Leonardo is an AI assistant", "The weather is nice today", False),
            ("I like programming", "She enjoys cooking", False),
        ]
    
    async def run_all_tests(self):
        """Run complete real NLI test suite."""
        logger.info("🔍 Starting Real NLI Verification Test Suite...")
        logger.info("📥 This will download HuggingFace models (may take a few minutes)")
        
        try:
            # Test 1: Model Loading
            logger.info("\n📋 Test 1: Real NLI Model Loading")
            await self.test_nli_model_loading()
            
            # Test 2: Basic Entailment
            logger.info("\n📋 Test 2: Basic Entailment Testing")
            await self.test_basic_entailment()
            
            # Test 3: Claim Verification
            logger.info("\n📋 Test 3: Research Claim Verification")
            await self.test_claim_verification()
            
            # Test 4: Citation Integration
            logger.info("\n📋 Test 4: Citation Store Integration")
            await self.test_citation_integration()
            
            # Test 5: Research Verifier
            logger.info("\n📋 Test 5: Complete Research Verifier")
            await self.test_research_verifier()
            
            # Final results
            self.print_final_results()
            
        except Exception as e:
            logger.error(f"❌ Test suite failed with error: {e}")
        
        return all(self.test_results.values())
    
    async def test_nli_model_loading(self):
        """Test real HuggingFace model loading."""
        try:
            logger.info("🧠 Loading real NLI model...")
            
            # Create NLI runner with production config
            config = {
                "backend": "local",
                "model": "typeform/distilbert-base-uncased-mnli",
                "entailment_threshold": 0.6,
                "batch_size": 16,
                "quantize": True,
                "testing_mode": False,  # REAL MODEL MODE
                "fallback_models": [
                    "MoritzLaurer/DeBERTa-v3-base-mnli"
                ]
            }
            
            nli_runner = LocalNLIRunner(config)
            
            # Attempt to initialize
            success = await nli_runner.initialize()
            
            if success:
                self.test_results["nli_model_loading"] = True
                logger.info(f"✅ Model loaded successfully: {nli_runner.model_name}")
                logger.info(f"   Device: {nli_runner.device}")
                logger.info(f"   Quantized: {nli_runner.quantize}")
                
                # Test basic functionality
                test_entails, test_confidence = nli_runner.entails(
                    "Test claim", ["Test evidence"]
                )
                logger.info(f"   Test inference: {test_entails} (confidence: {test_confidence:.3f})")
                
                nli_runner.shutdown()
            else:
                logger.error("❌ Failed to load NLI model")
                
        except Exception as e:
            logger.error(f"❌ NLI model loading error: {e}")
    
    async def test_basic_entailment(self):
        """Test basic entailment with real model."""
        if not self.test_results["nli_model_loading"]:
            logger.warning("⚠️ Skipping entailment test - model loading failed")
            return
        
        try:
            logger.info("🔍 Testing real entailment inference...")
            
            # Create NLI runner
            config = {
                "model": "typeform/distilbert-base-uncased-mnli",
                "entailment_threshold": 0.6,
                "testing_mode": False  # REAL MODEL MODE
            }
            nli_runner = LocalNLIRunner(config)
            
            if not await nli_runner.initialize():
                logger.error("❌ Failed to initialize NLI runner")
                return
            
            # Test multiple cases
            correct_predictions = 0
            total_cases = len(self.test_cases)
            
            logger.info(f"   Running {total_cases} entailment test cases...")
            
            for i, (claim, evidence, expected) in enumerate(self.test_cases, 1):
                entails, confidence = nli_runner.entails(claim, [evidence])
                
                # Check if prediction matches expected
                correct = (entails == expected)
                if correct:
                    correct_predictions += 1
                
                status = "✅" if correct else "❌"
                logger.info(f"   {i}. {status} Claim: '{claim[:30]}...'")
                logger.info(f"      Evidence: '{evidence[:30]}...'")
                logger.info(f"      Expected: {expected}, Got: {entails} (conf: {confidence:.3f})")
            
            accuracy = correct_predictions / total_cases
            logger.info(f"📊 Entailment Accuracy: {accuracy:.2%} ({correct_predictions}/{total_cases})")
            
            # Accept 70%+ accuracy as success (real NLI models aren't perfect)
            if accuracy >= 0.7:
                self.test_results["basic_entailment"] = True
                logger.info("✅ Basic entailment test passed")
            else:
                logger.warning("⚠️ Basic entailment accuracy below 70%")
            
            nli_runner.shutdown()
            
        except Exception as e:
            logger.error(f"❌ Basic entailment test error: {e}")
    
    async def test_claim_verification(self):
        """Test claim verification with real research scenario."""
        if not self.test_results["basic_entailment"]:
            logger.warning("⚠️ Skipping claim verification - basic entailment failed")
            return
        
        try:
            logger.info("🔬 Testing research claim verification...")
            
            # Create realistic research scenario
            research_claims = [
                "Leonardo da Vinci was an Italian Renaissance polymath",
                "He is famous for paintings like the Mona Lisa",
                "Da Vinci also designed flying machines and studied anatomy"
            ]
            
            evidence_sources = [
                "Leonardo da Vinci (1452-1519) was an Italian polymath of the Renaissance period, known for his work in art, science, and engineering.",
                "Among his most famous paintings are the Mona Lisa and The Last Supper, which showcase his mastery of artistic technique.",
                "Leonardo designed numerous inventions including flying machines, helicopters, and tanks, while also conducting detailed anatomical studies."
            ]
            
            # Create NLI runner
            config = {
                "model": "typeform/distilbert-base-uncased-mnli",
                "entailment_threshold": 0.6,
                "testing_mode": False
            }
            nli_runner = LocalNLIRunner(config)
            
            if not await nli_runner.initialize():
                logger.error("❌ Failed to initialize NLI runner")
                return
            
            # Verify each claim
            verified_claims = 0
            for i, claim in enumerate(research_claims, 1):
                entails, confidence = nli_runner.entails(claim, evidence_sources)
                
                status = "✅" if entails else "❌"
                logger.info(f"   {i}. {status} Claim: '{claim}'")
                logger.info(f"      Entails: {entails}, Confidence: {confidence:.3f}")
                
                if entails and confidence >= 0.6:
                    verified_claims += 1
            
            verification_rate = verified_claims / len(research_claims)
            logger.info(f"📊 Claim Verification Rate: {verification_rate:.2%} ({verified_claims}/{len(research_claims)})")
            
            if verification_rate >= 0.8:  # 80% of claims should verify
                self.test_results["claim_verification"] = True
                logger.info("✅ Claim verification test passed")
            
            nli_runner.shutdown()
            
        except Exception as e:
            logger.error(f"❌ Claim verification test error: {e}")
    
    async def test_citation_integration(self):
        """Test citation store integration with NLI."""
        try:
            logger.info("📚 Testing citation store integration...")
            
            # Create citation store
            citation_store = CitationStore()
            
            # Store content with citations
            content_id = citation_store.store_content(
                url="https://example.com/leonardo-article",
                title="Leonardo da Vinci Biography",
                text="Leonardo da Vinci (1452-1519) was an Italian Renaissance polymath. He painted the famous Mona Lisa and designed flying machines. His anatomical studies were groundbreaking for the time period.",
                metadata={"source": "test_content"}
            )
            
            # Create citation with span
            span = ContentSpan(start=0, end=50)  # "Leonardo da Vinci (1452-1519) was an Italian Rena"
            citation_source = citation_store.create_citation_source(content_id, span)
            
            if citation_source:
                logger.info(f"✅ Citation created: {citation_source.content_id}")
                logger.info(f"   Quote: '{citation_source.quote}'")
                logger.info(f"   Hash: {citation_source.hash[:16]}...")
                
                # Verify integrity
                integrity_ok = citation_store.verify_citation_integrity(
                    citation_store.create_claim_citation(
                        "Leonardo da Vinci was a Renaissance polymath",
                        [(content_id, span)]
                    )
                )
                
                if integrity_ok:
                    self.test_results["citation_integration"] = True
                    logger.info("✅ Citation integrity verified")
                else:
                    logger.error("❌ Citation integrity check failed")
            else:
                logger.error("❌ Failed to create citation source")
                
        except Exception as e:
            logger.error(f"❌ Citation integration test error: {e}")
    
    async def test_research_verifier(self):
        """Test complete research verifier system."""
        if not self.test_results["claim_verification"]:
            logger.warning("⚠️ Skipping research verifier - claim verification failed") 
            return
        
        try:
            logger.info("🔬 Testing complete research verifier...")
            
            # Create research verifier with real model
            config = {
                "nli": {
                    "backend": "local",
                    "model": "typeform/distilbert-base-uncased-mnli",
                    "entailment_threshold": 0.6,
                    "batch_size": 16,
                    "testing_mode": False  # REAL MODEL MODE
                },
                "coverage_threshold": 0.8,
                "min_sources_per_claim": 1
            }
            
            research_verifier = ResearchVerifier(config)
            
            if not await research_verifier.initialize():
                logger.error("❌ Failed to initialize research verifier")
                return
            
            # Create mock research tool result
            tool_call = {
                "tool": "web.deep_research",
                "args": {"query": "Leonardo da Vinci biography"},
                "meta": {"risk": "safe"}
            }
            
            tool_result = {
                "summary": "Leonardo da Vinci was a Renaissance artist and inventor who created masterpieces.",
                "citations": [],  # Would normally have proper citations
                "sources": ["https://example.com/leonardo"]
            }
            
            from leonardo.validation.validation_result import ValidationResult, RiskLevel
            validation_result = ValidationResult(
                approved=True,
                risk_level=RiskLevel.SAFE,
                tool_name="web.deep_research",
                validation_id="test_research_verifier_real",
                timestamp=datetime.now()
            )
            
            # Run research verification
            success = research_verifier.verify_research_tool_result(
                tool_call, tool_result, validation_result
            )
            
            if success:
                self.test_results["research_verifier"] = True
                logger.info("✅ Research verifier test passed")
                
                # Get verification stats
                stats = research_verifier.get_verification_stats()
                logger.info(f"   NLI Model: {stats['nli_model']['model_name']}")
                logger.info(f"   Loaded: {stats['nli_model']['loaded']}")
            else:
                logger.warning("⚠️ Research verifier returned warnings")
            
            await research_verifier.shutdown()
            
        except Exception as e:
            logger.error(f"❌ Research verifier test error: {e}")
    
    def print_final_results(self):
        """Print final test results summary."""
        logger.info("\n🎯 REAL NLI VERIFICATION TEST RESULTS:")
        logger.info("=" * 60)
        
        passed = 0
        total = len(self.test_results)
        
        for test_name, result in self.test_results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"   {test_name.replace('_', ' ').title()}: {status}")
            if result:
                passed += 1
        
        logger.info(f"\n📊 Overall Results: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
        
        if passed == total:
            logger.info("🎉 ALL REAL NLI VERIFICATION TESTS PASSED!")
            logger.info("🏆 Production NLI verification system is FULLY OPERATIONAL!")
            logger.info("\n🔍 Verification System Ready For:")
            logger.info("   ✅ Real claim verification against citations")
            logger.info("   ✅ Research result validation")
            logger.info("   ✅ Post-execution verification")
            logger.info("   ✅ Production deployment")
        elif passed >= total * 0.8:
            logger.info("🟡 MOSTLY SUCCESSFUL - Minor issues detected")
            logger.warning("   Some tests failed but core functionality works")
        else:
            logger.warning(f"🔴 MULTIPLE FAILURES - {total - passed} test(s) failed")
            logger.warning("   Review implementation before production use")


async def main():
    """Run the real NLI verification test suite."""
    test_suite = RealNLITestSuite()
    success = await test_suite.run_all_tests()
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
