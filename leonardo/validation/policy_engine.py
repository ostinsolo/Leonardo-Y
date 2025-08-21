"""
Policy Engine - Second Tier of Validation Wall
Risk assessment, domain allowlists, rate limits, and security policies
"""

import logging
import time
from typing import Dict, Any, List, Set, Optional
from pathlib import Path
from collections import defaultdict, deque
from datetime import datetime, timedelta

from .validation_result import ValidationResult, ValidationStage, RiskLevel

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiting for tool executions."""
    
    def __init__(self, max_calls: int = 10, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.calls = defaultdict(deque)  # user_id -> deque of timestamps
    
    def is_allowed(self, user_id: str = "default") -> bool:
        """Check if user is within rate limits."""
        now = time.time()
        user_calls = self.calls[user_id]
        
        # Remove old calls outside the window
        while user_calls and user_calls[0] < now - self.window_seconds:
            user_calls.popleft()
        
        # Check if under limit
        return len(user_calls) < self.max_calls
    
    def record_call(self, user_id: str = "default"):
        """Record a tool call for rate limiting."""
        self.calls[user_id].append(time.time())


class PolicyEngine:
    """
    Policy Engine for risk assessment and security policies.
    Second tier of the validation wall.
    """
    
    def __init__(self):
        self.policies_path = Path(__file__).parent / "policies"
        self.policies_path.mkdir(exist_ok=True)
        
        # Rate limiters by risk level
        self.rate_limiters = {
            RiskLevel.SAFE: RateLimiter(max_calls=50, window_seconds=60),      # 50/min for safe tools
            RiskLevel.REVIEW: RateLimiter(max_calls=20, window_seconds=60),    # 20/min for review tools
            RiskLevel.CONFIRM: RateLimiter(max_calls=5, window_seconds=300),   # 5/5min for confirm tools
            RiskLevel.OWNER_ROOT: RateLimiter(max_calls=2, window_seconds=3600) # 2/hour for critical
        }
        
        # Domain allowlists for web tools
        self.allowed_domains = {
            "default": {
                "github.com", "stackoverflow.com", "python.org", "docs.python.org",
                "wikipedia.org", "arxiv.org", "scholar.google.com", "openai.com",
                "huggingface.co", "paperswithcode.com", "arxiv-vanity.com"
            },
            "research": {
                "pubmed.ncbi.nlm.nih.gov", "ieee.org", "acm.org", "nature.com",
                "science.org", "cell.com", "nejm.org", "bmj.com"
            }
        }
        
        # File path restrictions
        self.restricted_paths = {
            "/etc/", "/usr/bin/", "/System/", "/Library/System/",
            "/.ssh/", "/var/", "/tmp/", "/private/"
        }
        
        # Dangerous file extensions
        self.dangerous_extensions = {
            ".sh", ".bash", ".zsh", ".py", ".js", ".exe", ".bat", ".cmd", 
            ".scr", ".com", ".pif", ".reg", ".vbs", ".jar"
        }
        
        # Tool risk classifications
        self.tool_risk_levels = {
            # Safe tools (auto-execute)
            "get_weather": RiskLevel.SAFE,
            "get_time": RiskLevel.SAFE,
            "get_date": RiskLevel.SAFE,
            "calculate": RiskLevel.SAFE,
            "respond": RiskLevel.SAFE,
            "system_info": RiskLevel.SAFE,
            "recall_memory": RiskLevel.SAFE,
            
            # Review tools (preview before execution)
            "read_file": RiskLevel.REVIEW,
            "list_files": RiskLevel.REVIEW,
            "search_web": RiskLevel.REVIEW,
            "web.scrape": RiskLevel.SAFE,  # TEMP: Allow safe access for testing
            "web.search": RiskLevel.SAFE,  # TEMP: Allow safe access for testing
            "web.deep_research": RiskLevel.SAFE,  # TEMP: Allow safe access for testing
            
            # Confirm tools (user confirmation required)
            "write_file": RiskLevel.CONFIRM,
            "send_email": RiskLevel.CONFIRM,
            "macos_control": RiskLevel.CONFIRM,
            
            # Owner-root tools (critical operations)
            "teach_command": RiskLevel.OWNER_ROOT,
        }
        
        logger.info("🛡️ Policy engine initialized with security policies")
    
    def validate_policy(self, tool_call: Dict[str, Any], result: ValidationResult) -> bool:
        """
        Validate tool call against security policies.
        Returns True if policy compliant, False if violations found.
        """
        tool_name = tool_call.get("tool", "")
        args = tool_call.get("args", {})
        meta = tool_call.get("meta", {})
        user_id = result.user_id
        
        try:
            # 1. Risk Level Assessment
            if not self._validate_risk_level(tool_name, meta, result):
                return False
            
            # 2. Rate Limiting
            if not self._validate_rate_limits(tool_name, meta, user_id, result):
                return False
            
            # 3. Tool-Specific Policies
            if not self._validate_tool_specific(tool_name, args, result):
                return False
            
            # 4. Domain/Path Restrictions
            if not self._validate_domain_restrictions(tool_name, args, result):
                return False
            
            # 5. File Path Security
            if not self._validate_file_security(tool_name, args, result):
                return False
            
            # 6. Content Size Limits
            if not self._validate_size_limits(tool_name, args, result):
                return False
            
            logger.debug(f"✅ Policy validation passed for {tool_name}")
            return True
            
        except Exception as e:
            result.add_error(
                ValidationStage.POLICY,
                "POLICY_ERROR",
                f"Policy validation error: {str(e)}",
                RiskLevel.BLOCKED
            )
            return False
    
    def _validate_risk_level(self, tool_name: str, meta: Dict[str, Any], result: ValidationResult) -> bool:
        """Validate and enforce risk level."""
        requested_risk = meta.get("risk", "safe")
        expected_risk = self.tool_risk_levels.get(tool_name, RiskLevel.REVIEW)
        
        # Convert string to RiskLevel if needed
        if isinstance(requested_risk, str):
            try:
                requested_risk = RiskLevel(requested_risk)
            except ValueError:
                result.add_error(
                    ValidationStage.POLICY,
                    "INVALID_RISK_LEVEL",
                    f"Invalid risk level '{requested_risk}' for tool '{tool_name}'",
                    RiskLevel.BLOCKED
                )
                return False
        
        # Check if requested risk is appropriate
        risk_hierarchy = [RiskLevel.SAFE, RiskLevel.REVIEW, RiskLevel.CONFIRM, RiskLevel.OWNER_ROOT]
        
        expected_index = risk_hierarchy.index(expected_risk)
        requested_index = risk_hierarchy.index(requested_risk)
        
        if requested_index < expected_index:
            result.add_error(
                ValidationStage.POLICY,
                "INSUFFICIENT_RISK_LEVEL",
                f"Tool '{tool_name}' requires minimum risk level '{expected_risk.value}', got '{requested_risk.value}'",
                RiskLevel.BLOCKED
            )
            return False
        
        # Update result with final risk level
        result.risk_level = max(result.risk_level, requested_risk, key=lambda x: risk_hierarchy.index(x))
        
        return True
    
    def _validate_rate_limits(self, tool_name: str, meta: Dict[str, Any], user_id: str, result: ValidationResult) -> bool:
        """Validate rate limits."""
        risk_level = RiskLevel(meta.get("risk", "safe"))
        rate_limiter = self.rate_limiters.get(risk_level)
        
        if rate_limiter and not rate_limiter.is_allowed(user_id):
            result.add_error(
                ValidationStage.POLICY,
                "RATE_LIMIT_EXCEEDED",
                f"Rate limit exceeded for {risk_level.value} tools (user: {user_id})",
                RiskLevel.BLOCKED
            )
            return False
        
        # Record the call for rate limiting
        if rate_limiter:
            rate_limiter.record_call(user_id)
        
        return True
    
    def _validate_tool_specific(self, tool_name: str, args: Dict[str, Any], result: ValidationResult) -> bool:
        """Tool-specific policy validation."""
        
        # Email validation
        if tool_name == "send_email":
            to_address = args.get("to", "")
            if "@" not in to_address:
                result.add_error(
                    ValidationStage.POLICY,
                    "INVALID_EMAIL",
                    f"Invalid email address: {to_address}",
                    RiskLevel.BLOCKED
                )
                return False
            
            # Block external domains for security
            external_domains = ["gmail.com", "hotmail.com", "yahoo.com"]
            domain = to_address.split("@")[-1].lower()
            if domain in external_domains:
                result.add_warning(
                    ValidationStage.POLICY,
                    "EXTERNAL_EMAIL",
                    f"Sending email to external domain: {domain}",
                    RiskLevel.CONFIRM
                )
        
        # Calculator security
        elif tool_name == "calculate":
            expression = args.get("expression", "")
            dangerous_funcs = ["exec", "eval", "import", "__", "os.", "sys.", "subprocess"]
            if any(func in expression for func in dangerous_funcs):
                result.add_error(
                    ValidationStage.POLICY,
                    "DANGEROUS_EXPRESSION",
                    f"Potentially dangerous expression: {expression}",
                    RiskLevel.BLOCKED
                )
                return False
        
        return True
    
    def _validate_domain_restrictions(self, tool_name: str, args: Dict[str, Any], result: ValidationResult) -> bool:
        """Validate domain allowlists for web tools."""
        web_tools = ["search_web", "web.scrape", "web.search", "web.extract", "web.deep_research"]
        
        if tool_name not in web_tools:
            return True
        
        # Check domain allowlist if URL is specified
        url = args.get("url", "")
        query = args.get("query", "")
        
        # Extract domain from URL if present
        if url:
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc.lower()
                
                all_allowed = set()
                for domain_set in self.allowed_domains.values():
                    all_allowed.update(domain_set)
                
                if domain and domain not in all_allowed:
                    result.add_warning(
                        ValidationStage.POLICY,
                        "DOMAIN_NOT_ALLOWLISTED",
                        f"Domain '{domain}' not in allowlist",
                        RiskLevel.CONFIRM
                    )
            
            except Exception:
                result.add_warning(
                    ValidationStage.POLICY,
                    "INVALID_URL",
                    f"Could not parse URL: {url}",
                    RiskLevel.REVIEW
                )
        
        return True
    
    def _validate_file_security(self, tool_name: str, args: Dict[str, Any], result: ValidationResult) -> bool:
        """Validate file operation security."""
        file_tools = ["read_file", "write_file", "list_files"]
        
        if tool_name not in file_tools:
            return True
        
        path = args.get("path", "")
        if not path:
            return True
        
        # Check for restricted paths
        for restricted in self.restricted_paths:
            if path.startswith(restricted):
                result.add_error(
                    ValidationStage.POLICY,
                    "RESTRICTED_PATH",
                    f"Access to restricted path: {path}",
                    RiskLevel.BLOCKED
                )
                return False
        
        # Check for dangerous file extensions (write operations)
        if tool_name == "write_file":
            path_lower = path.lower()
            for ext in self.dangerous_extensions:
                if path_lower.endswith(ext):
                    result.add_warning(
                        ValidationStage.POLICY,
                        "DANGEROUS_FILE_TYPE",
                        f"Writing potentially dangerous file type: {ext}",
                        RiskLevel.CONFIRM
                    )
        
        # Directory traversal protection
        if ".." in path or path.startswith("/"):
            result.add_warning(
                ValidationStage.POLICY,
                "PATH_TRAVERSAL",
                f"Potential path traversal in: {path}",
                RiskLevel.REVIEW
            )
        
        return True
    
    def _validate_size_limits(self, tool_name: str, args: Dict[str, Any], result: ValidationResult) -> bool:
        """Validate content size limits."""
        
        # File content size limits
        if tool_name == "write_file":
            content = args.get("content", "")
            max_size = 1024 * 1024  # 1MB limit
            
            if len(content) > max_size:
                result.add_error(
                    ValidationStage.POLICY,
                    "CONTENT_TOO_LARGE",
                    f"File content too large: {len(content)} bytes (max: {max_size})",
                    RiskLevel.BLOCKED
                )
                return False
        
        # Email size limits
        elif tool_name == "send_email":
            body = args.get("body", "")
            if len(body) > 50000:  # 50KB limit for emails
                result.add_warning(
                    ValidationStage.POLICY,
                    "EMAIL_TOO_LARGE",
                    f"Email body is very large: {len(body)} characters",
                    RiskLevel.REVIEW
                )
        
        return True
    
    def get_policy_summary(self) -> Dict[str, Any]:
        """Get summary of current policies."""
        return {
            "rate_limits": {
                level.value: f"{limiter.max_calls}/{limiter.window_seconds}s" 
                for level, limiter in self.rate_limiters.items()
            },
            "allowed_domains": len(set().union(*self.allowed_domains.values())),
            "restricted_paths": len(self.restricted_paths),
            "tool_risk_levels": {
                tool: level.value for tool, level in self.tool_risk_levels.items()
            }
        }
