#!/usr/bin/env python3
"""
Leonardo Interaction Logger
Collects and saves detailed interaction data for analysis and learning
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import time
import os

class InteractionLogger:
    """Logs Leonardo's voice interactions for analysis and improvement."""
    
    def __init__(self, logs_dir: str = "leonardo_logs"):
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        
        # Current session data
        self.session_start = datetime.now(timezone.utc)
        self.session_id = self.session_start.strftime("%Y%m%d_%H%M%S")
        self.interactions: List[Dict] = []
        self.session_metrics = {
            "total_interactions": 0,
            "successful_interactions": 0,
            "failed_interactions": 0,
            "average_response_time": 0.0,
            "audio_issues": 0,
            "transcription_issues": 0,
            "tts_issues": 0
        }
        
        self.logger = logging.getLogger(__name__)
        
        # Create session file
        self.session_file = self.logs_dir / f"leonardo_session_{self.session_id}.json"
        
        print(f"📊 Logging session to: {self.session_file}")
    
    def start_interaction(self) -> str:
        """Start a new interaction and return its ID."""
        interaction_id = f"{self.session_id}_{len(self.interactions) + 1:03d}"
        
        interaction = {
            "interaction_id": interaction_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "start_time": time.time(),
            "status": "in_progress",
            "user_input": {
                "raw_audio_duration": None,
                "transcription": None,
                "transcription_confidence": None,
                "language_detected": None
            },
            "ai_processing": {
                "response_text": None,
                "response_type": None,
                "processing_time": None,
                "conversation_context": None,
                "user_name": None
            },
            "audio_output": {
                "tts_text": None,
                "tts_duration": None,
                "playback_success": False
            },
            "metrics": {
                "total_time": None,
                "stt_time": None,
                "ai_time": None,
                "tts_time": None,
                "audio_playback_time": None
            },
            "issues": [],
            "success": False
        }
        
        self.interactions.append(interaction)
        return interaction_id
    
    def log_audio_input(self, interaction_id: str, duration: float, transcription: str, 
                       confidence: float = None, language: str = "en"):
        """Log audio input details."""
        interaction = self._get_interaction(interaction_id)
        if interaction:
            interaction["user_input"].update({
                "raw_audio_duration": duration,
                "transcription": transcription,
                "transcription_confidence": confidence,
                "language_detected": language
            })
    
    def log_ai_response(self, interaction_id: str, response_text: str, 
                       response_type: str, processing_time: float,
                       conversation_context: str = None, user_name: str = None):
        """Log AI response generation."""
        interaction = self._get_interaction(interaction_id)
        if interaction:
            interaction["ai_processing"].update({
                "response_text": response_text,
                "response_type": response_type,
                "processing_time": processing_time,
                "conversation_context": conversation_context,
                "user_name": user_name
            })
    
    def log_audio_output(self, interaction_id: str, tts_text: str, 
                        tts_duration: float, playback_success: bool):
        """Log audio output details."""
        interaction = self._get_interaction(interaction_id)
        if interaction:
            interaction["audio_output"].update({
                "tts_text": tts_text,
                "tts_duration": tts_duration,
                "playback_success": playback_success
            })
    
    def log_timing(self, interaction_id: str, phase: str, duration: float):
        """Log timing for different phases."""
        interaction = self._get_interaction(interaction_id)
        if interaction:
            interaction["metrics"][f"{phase}_time"] = duration
    
    def log_issue(self, interaction_id: str, issue_type: str, description: str):
        """Log an issue during interaction."""
        interaction = self._get_interaction(interaction_id)
        if interaction:
            interaction["issues"].append({
                "type": issue_type,
                "description": description,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Update session metrics
            if issue_type == "audio":
                self.session_metrics["audio_issues"] += 1
            elif issue_type == "transcription":
                self.session_metrics["transcription_issues"] += 1
            elif issue_type == "tts":
                self.session_metrics["tts_issues"] += 1
    
    def finish_interaction(self, interaction_id: str, success: bool = True):
        """Complete an interaction."""
        interaction = self._get_interaction(interaction_id)
        if interaction:
            end_time = time.time()
            interaction["status"] = "completed"
            interaction["success"] = success
            interaction["metrics"]["total_time"] = end_time - interaction["start_time"]
            
            # Update session metrics
            self.session_metrics["total_interactions"] += 1
            if success:
                self.session_metrics["successful_interactions"] += 1
            else:
                self.session_metrics["failed_interactions"] += 1
            
            # Update average response time
            if interaction["metrics"]["total_time"]:
                current_avg = self.session_metrics["average_response_time"]
                total_count = self.session_metrics["total_interactions"]
                new_avg = ((current_avg * (total_count - 1)) + interaction["metrics"]["total_time"]) / total_count
                self.session_metrics["average_response_time"] = new_avg
            
            # Save after each interaction
            self._save_session()
    
    def _get_interaction(self, interaction_id: str) -> Optional[Dict]:
        """Get interaction by ID."""
        for interaction in self.interactions:
            if interaction["interaction_id"] == interaction_id:
                return interaction
        return None
    
    def _save_session(self):
        """Save current session to file."""
        session_data = {
            "session_info": {
                "session_id": self.session_id,
                "start_time": self.session_start.isoformat(),
                "leonardo_version": "1.0.0",
                "environment": {
                    "platform": os.name,
                    "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
                }
            },
            "session_metrics": self.session_metrics,
            "interactions": self.interactions
        }
        
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save session: {e}")
    
    def get_session_summary(self) -> Dict:
        """Get current session summary."""
        return {
            "session_id": self.session_id,
            "duration": (datetime.now(timezone.utc) - self.session_start).total_seconds(),
            "interactions": self.session_metrics["total_interactions"],
            "success_rate": (
                self.session_metrics["successful_interactions"] / 
                max(1, self.session_metrics["total_interactions"])
            ) * 100,
            "avg_response_time": self.session_metrics["average_response_time"],
            "issues": {
                "audio": self.session_metrics["audio_issues"],
                "transcription": self.session_metrics["transcription_issues"],
                "tts": self.session_metrics["tts_issues"]
            }
        }
    
    def close_session(self):
        """Close and finalize the session."""
        self.session_metrics["session_duration"] = (
            datetime.now(timezone.utc) - self.session_start
        ).total_seconds()
        
        self._save_session()
        
        # Print session summary
        summary = self.get_session_summary()
        print(f"\n📊 SESSION SUMMARY ({self.session_id}):")
        print(f"   Duration: {summary['duration']:.1f}s")
        print(f"   Interactions: {summary['interactions']}")
        print(f"   Success Rate: {summary['success_rate']:.1f}%")
        print(f"   Avg Response Time: {summary['avg_response_time']:.2f}s")
        print(f"   Issues: Audio={summary['issues']['audio']}, STT={summary['issues']['transcription']}, TTS={summary['issues']['tts']}")
        print(f"   📁 Saved to: {self.session_file}")


def analyze_sessions(logs_dir: str = "leonardo_logs") -> Dict:
    """Analyze all Leonardo sessions for trends and improvements."""
    logs_path = Path(logs_dir)
    
    if not logs_path.exists():
        return {"error": "No logs directory found"}
    
    session_files = list(logs_path.glob("leonardo_session_*.json"))
    
    if not session_files:
        return {"error": "No session files found"}
    
    analysis = {
        "total_sessions": len(session_files),
        "total_interactions": 0,
        "success_rates": [],
        "response_times": [],
        "common_issues": {},
        "improvement_trends": {},
        "latest_session": None
    }
    
    for session_file in sorted(session_files):
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            metrics = session_data.get("session_metrics", {})
            
            analysis["total_interactions"] += metrics.get("total_interactions", 0)
            
            if metrics.get("total_interactions", 0) > 0:
                success_rate = (metrics.get("successful_interactions", 0) / 
                               metrics.get("total_interactions", 1)) * 100
                analysis["success_rates"].append(success_rate)
            
            if metrics.get("average_response_time"):
                analysis["response_times"].append(metrics["average_response_time"])
            
            # Track issues
            for issue_type in ["audio_issues", "transcription_issues", "tts_issues"]:
                count = metrics.get(issue_type, 0)
                if count > 0:
                    analysis["common_issues"][issue_type] = analysis["common_issues"].get(issue_type, 0) + count
            
            analysis["latest_session"] = session_data["session_info"]["session_id"]
            
        except Exception as e:
            print(f"⚠️ Error analyzing {session_file}: {e}")
    
    # Calculate averages
    if analysis["success_rates"]:
        analysis["average_success_rate"] = sum(analysis["success_rates"]) / len(analysis["success_rates"])
    
    if analysis["response_times"]:
        analysis["average_response_time"] = sum(analysis["response_times"]) / len(analysis["response_times"])
    
    return analysis


if __name__ == "__main__":
    # Test the logger
    logger = InteractionLogger()
    
    # Simulate an interaction
    interaction_id = logger.start_interaction()
    logger.log_audio_input(interaction_id, 2.5, "Hello Leonardo", 0.95)
    logger.log_ai_response(interaction_id, "Hello! How can I help?", "greeting", 0.1)
    logger.log_audio_output(interaction_id, "Hello! How can I help?", 1.2, True)
    logger.finish_interaction(interaction_id, True)
    
    logger.close_session()
    
    # Analyze sessions
    analysis = analyze_sessions()
    print(f"\n📈 ANALYSIS: {analysis}")
