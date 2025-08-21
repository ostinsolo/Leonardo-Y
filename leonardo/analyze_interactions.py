#!/usr/bin/env python3
"""
Leonardo Interaction Analysis Tool
Analyze logged interaction data to identify trends and improvements
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import matplotlib.pyplot as plt
import pandas as pd

# Add Leonardo to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from leonardo.interaction_logger import analyze_sessions

def detailed_session_analysis(logs_dir: str = "leonardo_logs"):
    """Provide detailed analysis of Leonardo sessions."""
    
    print("📊 LEONARDO INTERACTION ANALYSIS")
    print("=" * 50)
    
    # Basic analysis
    analysis = analyze_sessions(logs_dir)
    
    if "error" in analysis:
        print(f"❌ {analysis['error']}")
        return
    
    print(f"📋 OVERVIEW:")
    print(f"   Total Sessions: {analysis['total_sessions']}")
    print(f"   Total Interactions: {analysis['total_interactions']}")
    
    if analysis.get("average_success_rate"):
        print(f"   Average Success Rate: {analysis['average_success_rate']:.1f}%")
    
    if analysis.get("average_response_time"):
        print(f"   Average Response Time: {analysis['average_response_time']:.2f}s")
    
    print(f"   Latest Session: {analysis.get('latest_session', 'N/A')}")
    
    # Common issues
    if analysis["common_issues"]:
        print(f"\n⚠️  COMMON ISSUES:")
        for issue_type, count in analysis["common_issues"].items():
            issue_name = issue_type.replace("_", " ").title()
            print(f"   {issue_name}: {count}")
    
    # Load detailed session data for deeper analysis
    logs_path = Path(logs_dir)
    if logs_path.exists():
        session_files = list(logs_path.glob("leonardo_session_*.json"))
        
        if session_files:
            print(f"\n📈 DETAILED BREAKDOWN:")
            
            # Analyze response types
            response_types = {}
            all_response_times = []
            success_by_type = {}
            
            for session_file in sorted(session_files):
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    
                    for interaction in session_data.get("interactions", []):
                        # Track response types
                        response_type = interaction.get("ai_processing", {}).get("response_type", "unknown")
                        response_types[response_type] = response_types.get(response_type, 0) + 1
                        
                        # Track success by type
                        if response_type not in success_by_type:
                            success_by_type[response_type] = {"success": 0, "total": 0}
                        
                        success_by_type[response_type]["total"] += 1
                        if interaction.get("success", False):
                            success_by_type[response_type]["success"] += 1
                        
                        # Track response times
                        total_time = interaction.get("metrics", {}).get("total_time")
                        if total_time:
                            all_response_times.append(total_time)
                
                except Exception as e:
                    print(f"⚠️ Error analyzing {session_file}: {e}")
            
            # Response type breakdown
            print(f"\n🎯 RESPONSE TYPE DISTRIBUTION:")
            for response_type, count in sorted(response_types.items(), key=lambda x: x[1], reverse=True):
                success_rate = 0
                if response_type in success_by_type and success_by_type[response_type]["total"] > 0:
                    success_rate = (success_by_type[response_type]["success"] / 
                                  success_by_type[response_type]["total"]) * 100
                
                print(f"   {response_type.replace('_', ' ').title()}: {count} interactions ({success_rate:.1f}% success)")
            
            # Performance metrics
            if all_response_times:
                avg_time = sum(all_response_times) / len(all_response_times)
                min_time = min(all_response_times)
                max_time = max(all_response_times)
                
                print(f"\n⚡ PERFORMANCE METRICS:")
                print(f"   Average Response Time: {avg_time:.2f}s")
                print(f"   Fastest Response: {min_time:.2f}s")
                print(f"   Slowest Response: {max_time:.2f}s")
                
                # Performance distribution
                fast_responses = len([t for t in all_response_times if t < 2.0])
                medium_responses = len([t for t in all_response_times if 2.0 <= t < 5.0])
                slow_responses = len([t for t in all_response_times if t >= 5.0])
                
                total_responses = len(all_response_times)
                print(f"\n📊 RESPONSE SPEED DISTRIBUTION:")
                print(f"   Fast (<2s): {fast_responses} ({(fast_responses/total_responses)*100:.1f}%)")
                print(f"   Medium (2-5s): {medium_responses} ({(medium_responses/total_responses)*100:.1f}%)")
                print(f"   Slow (>5s): {slow_responses} ({(slow_responses/total_responses)*100:.1f}%)")

def find_improvement_opportunities(logs_dir: str = "leonardo_logs"):
    """Identify specific areas for improvement."""
    
    print(f"\n🚀 IMPROVEMENT OPPORTUNITIES:")
    print("=" * 35)
    
    logs_path = Path(logs_dir)
    if not logs_path.exists():
        print("❌ No logs directory found")
        return
    
    session_files = list(logs_path.glob("leonardo_session_*.json"))
    if not session_files:
        print("❌ No session files found")
        return
    
    issues_by_phase = {}
    common_failures = {}
    slow_phases = {}
    
    for session_file in sorted(session_files):
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            for interaction in session_data.get("interactions", []):
                # Analyze issues by phase
                for issue in interaction.get("issues", []):
                    issue_type = issue.get("type", "unknown")
                    issues_by_phase[issue_type] = issues_by_phase.get(issue_type, 0) + 1
                
                # Track common failure patterns
                if not interaction.get("success", False):
                    transcription = interaction.get("user_input", {}).get("transcription", "")
                    if transcription:
                        failure_pattern = f"Failed on: '{transcription[:30]}...'"
                        common_failures[failure_pattern] = common_failures.get(failure_pattern, 0) + 1
                
                # Identify slow phases
                metrics = interaction.get("metrics", {})
                for phase, time_taken in metrics.items():
                    if phase.endswith("_time") and time_taken:
                        if time_taken > 2.0:  # Slow threshold
                            slow_phases[phase] = slow_phases.get(phase, [])
                            slow_phases[phase].append(time_taken)
        
        except Exception as e:
            print(f"⚠️ Error analyzing {session_file}: {e}")
    
    # Report improvement opportunities
    if issues_by_phase:
        print("🔧 TOP ISSUE AREAS:")
        for issue_type, count in sorted(issues_by_phase.items(), key=lambda x: x[1], reverse=True):
            print(f"   {issue_type.title()}: {count} occurrences")
    
    if slow_phases:
        print(f"\n⏱️  SLOW PHASES:")
        for phase, times in slow_phases.items():
            avg_slow_time = sum(times) / len(times)
            print(f"   {phase.replace('_', ' ').title()}: {len(times)} slow instances (avg: {avg_slow_time:.2f}s)")
    
    if common_failures:
        print(f"\n❌ COMMON FAILURE PATTERNS:")
        for pattern, count in list(common_failures.items())[:5]:  # Top 5
            print(f"   {pattern} (x{count})")

def export_data_for_training(logs_dir: str = "leonardo_logs", output_file: str = "leonardo_training_data.json"):
    """Export interaction data in format suitable for LoRA training."""
    
    print(f"\n🎓 EXPORTING TRAINING DATA:")
    print("=" * 32)
    
    logs_path = Path(logs_dir)
    session_files = list(logs_path.glob("leonardo_session_*.json"))
    
    training_data = []
    
    for session_file in sorted(session_files):
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            for interaction in session_data.get("interactions", []):
                if interaction.get("success", False):
                    user_input = interaction.get("user_input", {}).get("transcription", "")
                    ai_response = interaction.get("ai_processing", {}).get("response_text", "")
                    response_type = interaction.get("ai_processing", {}).get("response_type", "")
                    
                    if user_input and ai_response:
                        training_example = {
                            "instruction": user_input,
                            "input": "",
                            "output": ai_response,
                            "category": response_type,
                            "success": True,
                            "timestamp": interaction.get("timestamp")
                        }
                        training_data.append(training_example)
        
        except Exception as e:
            print(f"⚠️ Error processing {session_file}: {e}")
    
    if training_data:
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(training_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Exported {len(training_data)} training examples to: {output_path}")
        
        # Summary by category
        categories = {}
        for example in training_data:
            category = example.get("category", "unknown")
            categories[category] = categories.get(category, 0) + 1
        
        print(f"\n📊 TRAINING DATA BREAKDOWN:")
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"   {category.replace('_', ' ').title()}: {count} examples")
    
    else:
        print("❌ No successful interactions found for training data")

if __name__ == "__main__":
    # Run comprehensive analysis
    detailed_session_analysis()
    find_improvement_opportunities()
    export_data_for_training()
    
    print(f"\n✨ Analysis complete!")
    print(f"💡 Use this data to:")
    print(f"   • Identify areas needing improvement")
    print(f"   • Train LoRA adapters with real usage data")
    print(f"   • Track Leonardo's learning progress over time")
