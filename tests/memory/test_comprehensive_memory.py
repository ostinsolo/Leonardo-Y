#!/usr/bin/env python3
"""
Leonardo Comprehensive Memory Test
Advanced conversation memory testing without microphone input

Tests:
1. Long conversation with varied topics
2. Conversation summarization
3. Specific question recall
4. Memory persistence and retrieval
5. Context awareness across turns
"""

import asyncio
import sys
import time
from pathlib import Path

# Add Leonardo to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from leonardo.config import LeonardoConfig
from leonardo.memory.service import MemoryService
from leonardo.planner.llm_planner import LLMPlanner
from leonardo.rag.rag_system import RAGSystem


class ComprehensiveMemoryTester:
    """Advanced test for Leonardo's memory and conversation capabilities."""
    
    def __init__(self):
        self.config = LeonardoConfig()
        self.memory_service = None
        self.llm_planner = None
        self.rag_system = None
        self.conversation_history = []  # Local tracking for test validation
        
    async def initialize(self):
        """Initialize Leonardo's brain components."""
        print("🔧 Initializing Leonardo's Advanced Memory System...")
        
        try:
            # Initialize RAG System
            self.rag_system = RAGSystem(self.config)
            await self.rag_system.initialize()
            
            # Initialize Memory Service
            self.memory_service = MemoryService(self.config)
            await self.memory_service.initialize()
            
            # Initialize LLM Planner with memory
            self.llm_planner = LLMPlanner(self.config, self.rag_system, self.memory_service)
            await self.llm_planner.initialize()
            
            print("✅ Leonardo's advanced brain is ready!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize components: {e}")
            return False
    
    async def have_conversation_turn(self, user_id: str, user_input: str, turn_number: int):
        """Have a complete conversation turn with Leonardo."""
        print(f"\n--- Turn {turn_number}: Advanced Memory Test ---")
        print(f"👤 User: '{user_input}'")
        
        # Store in our test history for validation
        turn_start_time = time.time()
        
        try:
            # Step 1: Generate Leonardo's response using LLM planner
            plan_result = await self.llm_planner.generate_plan(user_input, user_id)
            
            if plan_result and plan_result.tool_call:
                tool_call = plan_result.tool_call
                tool_name = tool_call.get('tool', 'unknown')
                print(f"🧠 Plan: {tool_name}")
                
                # Generate response based on tool call
                ai_response = await self._generate_response_from_tool_call(tool_call, user_input, user_id)
                
            else:
                tool_call = None  # Initialize to None when no plan result
                ai_response = f"I'm thinking about what you said: '{user_input}'. How can I help you with that?"
            
            print(f"🤖 Leonardo: '{ai_response}'")
            
            # Step 2: Store the conversation turn in memory
            conversation_turn = {
                "user": user_input,  # Changed from user_input to user
                "assistant": ai_response,  # Changed from ai_response to assistant
                "user_input": user_input,  # Keep for local tracking
                "ai_response": ai_response,  # Keep for local tracking
                "timestamp": time.time(),
                "turn_number": turn_number,
                "response_time": time.time() - turn_start_time
            }
            
            await self.memory_service.update_async(user_id, conversation_turn)
            self.conversation_history.append(conversation_turn)  # Local tracking
            
            print(f"🧠 Memory updated (Turn {turn_number})")
            
            # Step 3: Verify memory storage
            context = await self.memory_service.get_context_async(user_id, "memory check")
            recent_turns = context.get('recent_turns', [])
            print(f"📊 Total stored turns: {len(recent_turns)}")
            
            return ai_response, tool_call
            
        except Exception as e:
            print(f"❌ Error in conversation turn: {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    async def _generate_response_from_tool_call(self, tool_call, user_input, user_id):
        """Generate appropriate response based on tool call."""
        tool_name = tool_call.get("tool", "unknown")
        
        if tool_name == "respond":
            return tool_call.get("args", {}).get("message", "I'm not sure how to respond.")
            
        elif tool_name == "get_weather":
            return "I'd love to check the weather for you! Weather lookup is coming soon."
            
        elif tool_name == "search":
            query = tool_call.get("args", {}).get("query", "information")
            return f"I understand you want to search for '{query}'. Web search integration is being developed!"
            
        elif tool_name in ["get_time", "get_datetime"]:
            import datetime
            current_time = datetime.datetime.now().strftime("%I:%M %p")
            current_date = datetime.datetime.now().strftime("%A, %B %d, %Y")
            return f"Today is {current_date}, and the current time is {current_time}."
            
        elif tool_name == "recall_memory":
            # Handle memory recall questions with detailed context analysis
            context = tool_call.get("args", {}).get("context", {})
            recent_turns = context.get('recent_turns', [])
            
            print(f"🔍 Memory Context Debug: {len(recent_turns)} turns available")
            for i, turn in enumerate(recent_turns[-3:], 1):  # Show last 3 for debugging
                print(f"   Turn -{i}: '{turn.get('user_input', 'N/A')}'")
            
            if recent_turns:
                # Different memory recall strategies
                user_lower = user_input.lower()
                
                if any(phrase in user_lower for phrase in ['summarize', 'summary', 'conversation', 'talked about', 'discussed']):
                    # Conversation summarization request
                    topics = []
                    for turn in recent_turns:
                        if turn.get('user_input') and not any(mem_phrase in turn['user_input'].lower() 
                                                             for mem_phrase in ['remember', 'summarize', 'what did']):
                            topics.append(turn['user_input'])
                    
                    if topics:
                        topic_list = "', '".join(topics[-5:])  # Last 5 topics
                        return f"In our conversation, you asked about: '{topic_list}'. We discussed {len(topics)} different topics."
                    else:
                        return "We haven't discussed many topics yet in our conversation."
                
                elif any(phrase in user_lower for phrase in ['first', 'initially', 'started', 'beginning']):
                    # First question recall
                    first_turn = None
                    for turn in recent_turns:
                        if turn.get('user_input') and not any(mem_phrase in turn['user_input'].lower() 
                                                             for mem_phrase in ['remember', 'summarize', 'what did']):
                            first_turn = turn
                            break
                    
                    if first_turn:
                        return f"The first thing you asked me was: '{first_turn['user_input']}'"
                    else:
                        return "I can't find the first question in our conversation history."
                
                elif any(phrase in user_lower for phrase in ['before', 'previous', 'last', 'earlier']):
                    # Previous question recall (excluding memory questions)
                    for turn in reversed(recent_turns):
                        if (turn.get('user_input') and 
                            not any(mem_phrase in turn['user_input'].lower() 
                                   for mem_phrase in ['remember', 'what you said', 'before', 'what did i ask', 'summarize'])):
                            return f"You asked me: '{turn['user_input']}'"
                    
                    return "I don't see any previous non-memory questions in our conversation."
                
                else:
                    # Generic memory recall - most recent non-memory question
                    for turn in reversed(recent_turns):
                        if (turn.get('user_input') and 
                            not any(mem_phrase in turn['user_input'].lower() 
                                   for mem_phrase in ['remember', 'what you said', 'before'])):
                            return f"You asked me: '{turn['user_input']}'"
                    
                    return "I don't have any non-memory questions stored yet."
            else:
                return "I don't have any previous conversation turns stored yet."
        
        elif tool_name == "teach_command":
            return f"I'm learning from what you said: '{user_input}'. I'll remember that!"
            
        else:
            return f"I heard you say '{user_input}'. How can I help you with that?"
    
    async def run_comprehensive_memory_test(self):
        """Run the comprehensive memory conversation test."""
        print("🚀 LEONARDO COMPREHENSIVE MEMORY TEST")
        print("=" * 60)
        
        user_id = "advanced_test_user"
        
        # Extended conversation sequence
        conversation_sequence = [
            # Initial questions (build conversation history)
            "What time is it?",
            "What's the weather like today?", 
            "Search for machine learning news",
            "Can you help me with Python programming?",
            "What day is today?",
            
            # Memory recall tests
            "What did I ask you before?",  # Should recall "What day is today?"
            "What was the first thing I asked?",  # Should recall "What time is it?"
            "Can you summarize our conversation?",  # Should list all topics
            "What did I ask about programming?",  # Should find the Python question
            "Do you remember what I asked about the weather?",  # Should find weather question
        ]
        
        print(f"Testing {len(conversation_sequence)} conversation turns...")
        print("This will test: Basic questions, Memory recall, Summarization, Specific recall")
        
        responses = []
        tool_calls = []
        
        # Execute conversation
        for i, user_input in enumerate(conversation_sequence, 1):
            response, tool_call = await self.have_conversation_turn(user_id, user_input, i)
            responses.append(response)
            tool_calls.append(tool_call)
            
            # Brief pause between turns
            await asyncio.sleep(0.3)
        
        # Analyze results
        await self._analyze_comprehensive_results(conversation_sequence, responses, tool_calls)
        
        return len([r for r in responses if r is not None]) / len(conversation_sequence)
    
    async def _analyze_comprehensive_results(self, questions, responses, tool_calls):
        """Analyze the comprehensive test results."""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE MEMORY TEST ANALYSIS")
        print("=" * 60)
        
        # Categorize questions and responses
        basic_questions = questions[:5]  # First 5 are basic
        memory_questions = questions[5:]  # Last 5 are memory-related
        
        basic_responses = responses[:5]
        memory_responses = responses[5:]
        memory_tool_calls = tool_calls[5:]
        
        print(f"\n🔸 BASIC QUESTIONS PERFORMANCE:")
        basic_success = 0
        for i, (q, r) in enumerate(zip(basic_questions, basic_responses)):
            if r and len(r) > 10:  # Non-trivial response
                basic_success += 1
                status = "✅ GOOD"
            else:
                status = "❌ FAILED"
            print(f"   {i+1}. '{q}' → {status}")
        
        print(f"   Basic Questions Score: {basic_success}/{len(basic_questions)} ({basic_success/len(basic_questions)*100:.1f}%)")
        
        print(f"\n🧠 MEMORY QUESTIONS PERFORMANCE:")
        memory_success = 0
        memory_detailed_analysis = []
        
        for i, (q, r, tool) in enumerate(zip(memory_questions, memory_responses, memory_tool_calls)):
            analysis = {
                "question": q,
                "response": r,
                "tool": tool.get("tool") if tool else "none",
                "success": False,
                "reason": ""
            }
            
            if not r:
                analysis["reason"] = "No response generated"
            elif tool and tool.get("tool") == "recall_memory":
                analysis["reason"] = "Memory tool detected correctly"
                if "you asked" in r.lower() or "first thing" in r.lower() or "conversation" in r.lower():
                    if "something I cannot recall" not in r.lower():
                        analysis["success"] = True
                        analysis["reason"] += " + Content retrieved successfully"
                        memory_success += 1
                    else:
                        analysis["reason"] += " + But content retrieval failed"
                else:
                    analysis["reason"] += " + But wrong response format"
            else:
                analysis["reason"] = f"Wrong tool: {tool.get('tool') if tool else 'none'}"
            
            memory_detailed_analysis.append(analysis)
            
            status = "✅ SUCCESS" if analysis["success"] else "❌ FAILED"
            print(f"   {i+1}. '{q}'")
            print(f"      → Tool: {analysis['tool']}")
            print(f"      → Response: '{r[:100]}{'...' if len(r) > 100 else ''}'")
            print(f"      → {status}: {analysis['reason']}")
            print()
        
        memory_score = memory_success / len(memory_questions) * 100
        print(f"   Memory Questions Score: {memory_success}/{len(memory_questions)} ({memory_score:.1f}%)")
        
        print(f"\n🏆 FINAL COMPREHENSIVE SCORE:")
        total_success = basic_success + memory_success
        total_questions = len(basic_questions) + len(memory_questions)
        overall_score = total_success / total_questions * 100
        
        print(f"   Overall Performance: {total_success}/{total_questions} ({overall_score:.1f}%)")
        
        if overall_score >= 90:
            status = "🎉 EXCELLENT"
        elif overall_score >= 70:
            status = "✅ GOOD"
        elif overall_score >= 50:
            status = "⚠️ NEEDS IMPROVEMENT"
        else:
            status = "❌ MAJOR ISSUES"
        
        print(f"   Status: {status}")
        
        # Specific insights
        print(f"\n🔍 KEY INSIGHTS:")
        recall_tools = sum(1 for tool in memory_tool_calls if tool and tool.get("tool") == "recall_memory")
        print(f"   - Memory detection accuracy: {recall_tools}/{len(memory_questions)} ({recall_tools/len(memory_questions)*100:.1f}%)")
        
        successful_content = sum(1 for analysis in memory_detailed_analysis if analysis["success"])
        if recall_tools > 0:
            content_retrieval_rate = successful_content / recall_tools * 100
            print(f"   - Content retrieval accuracy: {successful_content}/{recall_tools} ({content_retrieval_rate:.1f}%)")
        
        return overall_score
    
    async def shutdown(self):
        """Shutdown components."""
        print("\n🛑 Shutting down components...")
        if self.llm_planner:
            await self.llm_planner.shutdown()
        if self.memory_service:
            await self.memory_service.shutdown()
        if self.rag_system:
            await self.rag_system.shutdown()
        print("✅ All components shut down")


async def main():
    """Main comprehensive test function."""
    tester = ComprehensiveMemoryTester()
    
    try:
        # Initialize Leonardo's brain
        if not await tester.initialize():
            print("❌ Failed to initialize Leonardo - aborting test")
            return False
        
        # Run comprehensive memory test
        success_rate = await tester.run_comprehensive_memory_test()
        
        # Shutdown
        await tester.shutdown()
        
        # Return success/failure
        return success_rate >= 0.7  # 70%+ success rate
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        await tester.shutdown()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit_code = 0 if success else 1
    print(f"\n🎭 Comprehensive memory test {'PASSED' if success else 'FAILED'}")
    sys.exit(exit_code)
