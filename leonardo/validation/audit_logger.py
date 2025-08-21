"""
Audit Logger - Compliance and Security Logging
Tracks all validation decisions for security and compliance
"""

import json
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime
import uuid

from .validation_result import ValidationResult, ValidationStage, RiskLevel

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Audit logging system for validation wall decisions.
    Provides compliance trail and security monitoring.
    """
    
    def __init__(self, audit_dir: Optional[Union[str, Path]] = None):
        if isinstance(audit_dir, str):
            self.audit_dir = Path(audit_dir)
        else:
            self.audit_dir = audit_dir or Path("leonardo_audit_logs")
        self.audit_dir.mkdir(exist_ok=True)
        
        # Create log files
        self.validation_log = self.audit_dir / "validation_decisions.jsonl"
        self.security_log = self.audit_dir / "security_events.jsonl"
        self.compliance_log = self.audit_dir / "compliance_audit.jsonl"
        
        # Metrics tracking
        self.session_metrics = {
            "total_validations": 0,
            "approved": 0,
            "blocked": 0,
            "user_confirmations": 0,
            "security_violations": 0,
            "policy_violations": 0,
            "schema_violations": 0,
            "linter_violations": 0
        }
        
        logger.info(f"🛡️ Audit logger initialized: {self.audit_dir}")
    
    def log_validation_result(self, tool_call: Dict[str, Any], result: ValidationResult) -> str:
        """
        Log complete validation result for audit trail.
        Returns audit record ID.
        """
        try:
            # Generate audit record
            audit_record = {
                "audit_id": str(uuid.uuid4()),
                "timestamp": datetime.now().isoformat(),
                "validation_id": result.validation_id,
                "user_id": result.user_id,
                "session_id": result.session_id,
                
                # Tool call details
                "tool_call": {
                    "tool": tool_call.get("tool", ""),
                    "args_summary": self._summarize_args(tool_call.get("args", {})),
                    "requested_risk": tool_call.get("meta", {}).get("risk", "")
                },
                
                # Validation result
                "result": {
                    "approved": result.approved,
                    "final_risk_level": result.risk_level.value,
                    "requires_confirmation": result.requires_confirmation,
                    "requires_dry_run": result.requires_dry_run,
                    "execution_timeout": result.execution_timeout
                },
                
                # Issues found
                "errors": [
                    {
                        "stage": error.stage.value,
                        "code": error.code,
                        "message": error.message,
                        "severity": error.severity.value
                    }
                    for error in result.errors
                ],
                "warnings": [
                    {
                        "stage": warning.stage.value,
                        "code": warning.code,
                        "message": warning.message,
                        "severity": warning.severity.value
                    }
                    for warning in result.warnings
                ],
                
                # Validation stages
                "stages_passed": [stage.value for stage in result.stages_passed],
                "metadata": result.metadata
            }
            
            # Write to validation log
            self._write_log_entry(self.validation_log, audit_record)
            
            # Update metrics
            self._update_metrics(result)
            
            # Log security events if any
            self._log_security_events(audit_record, result)
            
            # Log compliance events
            self._log_compliance_events(audit_record, result)
            
            return audit_record["audit_id"]
            
        except Exception as e:
            logger.error(f"❌ Failed to log validation result: {e}")
            return "audit_error"
    
    def log_execution_result(self, audit_id: str, execution_result: Dict[str, Any]):
        """Log tool execution result linked to validation audit."""
        try:
            execution_record = {
                "audit_id": audit_id,
                "timestamp": datetime.now().isoformat(),
                "execution": {
                    "success": execution_result.get("success", False),
                    "duration_ms": execution_result.get("duration_ms", 0),
                    "output_size": len(str(execution_result.get("result", ""))),
                    "error": execution_result.get("error", "")
                }
            }
            
            self._write_log_entry(self.validation_log, execution_record)
            
        except Exception as e:
            logger.error(f"❌ Failed to log execution result: {e}")
    
    def _summarize_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Summarize arguments for logging (remove sensitive data)."""
        summary = {}
        
        for key, value in args.items():
            # Mask sensitive fields
            if key.lower() in ["password", "token", "key", "secret", "auth"]:
                summary[key] = "***MASKED***"
            elif isinstance(value, str) and len(value) > 500:
                summary[key] = f"<large_content_{len(value)}_chars>"
            else:
                summary[key] = value
        
        return summary
    
    def _update_metrics(self, result: ValidationResult):
        """Update session metrics."""
        self.session_metrics["total_validations"] += 1
        
        if result.approved:
            self.session_metrics["approved"] += 1
        else:
            self.session_metrics["blocked"] += 1
        
        if result.requires_confirmation:
            self.session_metrics["user_confirmations"] += 1
        
        # Count violations by stage
        for error in result.errors:
            if error.stage == ValidationStage.SCHEMA:
                self.session_metrics["schema_violations"] += 1
            elif error.stage == ValidationStage.POLICY:
                self.session_metrics["policy_violations"] += 1
            elif error.stage == ValidationStage.LINTER:
                self.session_metrics["linter_violations"] += 1
            
            if error.severity == RiskLevel.BLOCKED:
                self.session_metrics["security_violations"] += 1
    
    def _log_security_events(self, audit_record: Dict[str, Any], result: ValidationResult):
        """Log security-relevant events."""
        security_events = []
        
        # Blocked operations
        if not result.approved:
            security_events.append({
                "event_type": "BLOCKED_OPERATION",
                "severity": "HIGH",
                "tool": audit_record["tool_call"]["tool"],
                "reason": "Validation failed",
                "error_count": len(result.errors)
            })
        
        # High-risk operations
        if result.risk_level == RiskLevel.OWNER_ROOT:
            security_events.append({
                "event_type": "CRITICAL_OPERATION",
                "severity": "CRITICAL",
                "tool": audit_record["tool_call"]["tool"],
                "requires_owner_auth": True
            })
        
        # Policy violations
        policy_errors = [e for e in result.errors if e.stage == ValidationStage.POLICY]
        for error in policy_errors:
            security_events.append({
                "event_type": "POLICY_VIOLATION",
                "severity": "HIGH",
                "code": error.code,
                "message": error.message
            })
        
        # Write security events
        for event in security_events:
            security_record = {
                **audit_record,
                "security_event": event
            }
            self._write_log_entry(self.security_log, security_record)
    
    def _log_compliance_events(self, audit_record: Dict[str, Any], result: ValidationResult):
        """Log compliance-relevant events."""
        compliance_record = {
            "audit_id": audit_record["audit_id"],
            "timestamp": audit_record["timestamp"],
            "user_id": audit_record["user_id"],
            "tool": audit_record["tool_call"]["tool"],
            "compliance": {
                "validation_completed": True,
                "all_stages_passed": len(result.errors) == 0,
                "user_confirmation_required": result.requires_confirmation,
                "audit_trail_complete": True,
                "risk_assessment": result.risk_level.value
            }
        }
        
        self._write_log_entry(self.compliance_log, compliance_record)
    
    def _write_log_entry(self, log_file: Path, record: Dict[str, Any]):
        """Write a JSON log entry to file."""
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"❌ Failed to write log entry to {log_file}: {e}")
    
    def get_session_metrics(self) -> Dict[str, Any]:
        """Get current session metrics."""
        return self.session_metrics.copy()
    
    def get_recent_validations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent validation records."""
        try:
            records = []
            if self.validation_log.exists():
                with open(self.validation_log, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    
                # Get the last N lines
                for line in lines[-limit:]:
                    try:
                        record = json.loads(line.strip())
                        if "tool_call" in record:  # Validation record, not execution
                            records.append(record)
                    except json.JSONDecodeError:
                        continue
            
            return records
            
        except Exception as e:
            logger.error(f"❌ Failed to read recent validations: {e}")
            return []
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security events summary."""
        try:
            events = []
            if self.security_log.exists():
                with open(self.security_log, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            record = json.loads(line.strip())
                            events.append(record["security_event"])
                        except (json.JSONDecodeError, KeyError):
                            continue
            
            # Summarize events
            event_counts = {}
            for event in events:
                event_type = event.get("event_type", "UNKNOWN")
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            return {
                "total_security_events": len(events),
                "event_breakdown": event_counts,
                "recent_events": events[-5:]  # Last 5 events
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get security summary: {e}")
            return {"error": str(e)}
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Clean up audit logs older than specified days."""
        try:
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            
            for log_file in [self.validation_log, self.security_log, self.compliance_log]:
                if not log_file.exists():
                    continue
                
                # Read and filter records
                retained_records = []
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            record = json.loads(line.strip())
                            record_time = datetime.fromisoformat(record["timestamp"]).timestamp()
                            if record_time >= cutoff_date:
                                retained_records.append(line)
                        except (json.JSONDecodeError, KeyError, ValueError):
                            continue
                
                # Rewrite file with retained records
                with open(log_file, "w", encoding="utf-8") as f:
                    f.writelines(retained_records)
                
                logger.info(f"🧹 Cleaned up {log_file.name}: {len(retained_records)} records retained")
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup old logs: {e}")
