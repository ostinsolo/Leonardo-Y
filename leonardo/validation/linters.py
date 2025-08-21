"""
Code Linters - Third Tier of Validation Wall
AST analysis and safety checks for dangerous operations
"""

import ast
import re
import logging
from typing import Dict, Any, List, Set, Optional

from .validation_result import ValidationResult, ValidationStage, RiskLevel

logger = logging.getLogger(__name__)


class PythonCodeLinter:
    """AST-based Python code safety analysis."""
    
    def __init__(self):
        # Dangerous Python functions and modules
        self.dangerous_imports = {
            "os", "sys", "subprocess", "shutil", "glob", "pathlib",
            "socket", "urllib", "requests", "http", "ftplib", "smtplib",
            "pickle", "marshal", "eval", "exec", "compile", "__import__"
        }
        
        # Dangerous function calls
        self.dangerous_functions = {
            "exec", "eval", "compile", "__import__", "open", "input",
            "raw_input", "file", "execfile", "reload", "delattr", "setattr"
        }
        
        # Dangerous attributes/methods
        self.dangerous_attributes = {
            "__class__", "__bases__", "__subclasses__", "__globals__",
            "__locals__", "__dict__", "__code__", "__func__"
        }
    
    def lint_python_code(self, code: str, result: ValidationResult) -> bool:
        """Lint Python code for security issues."""
        try:
            # Parse the AST
            tree = ast.parse(code)
            
            # Analyze the AST
            issues = []
            for node in ast.walk(tree):
                issues.extend(self._analyze_node(node))
            
            # Report issues
            for issue_type, message, severity in issues:
                if severity == "error":
                    result.add_error(
                        ValidationStage.LINTER,
                        f"PYTHON_{issue_type}",
                        message,
                        RiskLevel.BLOCKED
                    )
                else:
                    result.add_warning(
                        ValidationStage.LINTER,
                        f"PYTHON_{issue_type}",
                        message,
                        RiskLevel.CONFIRM
                    )
            
            # Return False if any blocking errors found
            return not any(severity == "error" for _, _, severity in issues)
            
        except SyntaxError as e:
            result.add_error(
                ValidationStage.LINTER,
                "PYTHON_SYNTAX_ERROR",
                f"Python syntax error: {e}",
                RiskLevel.BLOCKED
            )
            return False
        except Exception as e:
            result.add_warning(
                ValidationStage.LINTER,
                "PYTHON_LINT_ERROR",
                f"Python linting error: {e}",
                RiskLevel.REVIEW
            )
            return True
    
    def _analyze_node(self, node: ast.AST) -> List[tuple]:
        """Analyze a single AST node for security issues."""
        issues = []
        
        # Import analysis
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                module_name = alias.name
                if module_name in self.dangerous_imports:
                    issues.append((
                        "DANGEROUS_IMPORT",
                        f"Dangerous import: {module_name}",
                        "error"
                    ))
        
        # Function call analysis
        elif isinstance(node, ast.Call):
            func_name = self._get_function_name(node.func)
            if func_name in self.dangerous_functions:
                issues.append((
                    "DANGEROUS_FUNCTION",
                    f"Dangerous function call: {func_name}",
                    "error"
                ))
        
        # Attribute access analysis
        elif isinstance(node, ast.Attribute):
            if node.attr in self.dangerous_attributes:
                issues.append((
                    "DANGEROUS_ATTRIBUTE",
                    f"Dangerous attribute access: {node.attr}",
                    "warning"
                ))
        
        return issues
    
    def _get_function_name(self, func_node: ast.AST) -> str:
        """Extract function name from AST node."""
        if isinstance(func_node, ast.Name):
            return func_node.id
        elif isinstance(func_node, ast.Attribute):
            return func_node.attr
        else:
            return ""


class ShellCodeLinter:
    """Shell script safety analysis."""
    
    def __init__(self):
        # Dangerous shell commands
        self.dangerous_commands = {
            "rm", "rmdir", "mv", "cp", "dd", "mkfs", "fdisk",
            "sudo", "su", "chmod", "chown", "chgrp",
            "curl", "wget", "nc", "netcat", "telnet", "ssh",
            "eval", "exec", "source", ".",
            "kill", "killall", "pkill"
        }
        
        # Dangerous patterns
        self.dangerous_patterns = [
            r"rm\s+-rf\s+/",  # Recursive delete from root
            r">\s*/dev/\w+",   # Writing to devices
            r"\|\s*sh\s*$",    # Piping to shell
            r"curl.*\|\s*sh",  # Download and execute
            r"wget.*\|\s*sh",  # Download and execute
            r"\$\([^)]*\)",    # Command substitution
            r"`[^`]*`",        # Backtick command substitution
        ]
    
    def lint_shell_code(self, code: str, result: ValidationResult) -> bool:
        """Lint shell code for security issues."""
        try:
            lines = code.split('\n')
            issues_found = False
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Check for dangerous commands
                for cmd in self.dangerous_commands:
                    if re.search(rf'\b{re.escape(cmd)}\b', line):
                        result.add_warning(
                            ValidationStage.LINTER,
                            "SHELL_DANGEROUS_COMMAND",
                            f"Dangerous shell command '{cmd}' at line {line_num}: {line}",
                            RiskLevel.CONFIRM
                        )
                
                # Check for dangerous patterns
                for pattern in self.dangerous_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        result.add_error(
                            ValidationStage.LINTER,
                            "SHELL_DANGEROUS_PATTERN",
                            f"Dangerous shell pattern at line {line_num}: {line}",
                            RiskLevel.BLOCKED
                        )
                        issues_found = True
            
            return not issues_found
            
        except Exception as e:
            result.add_warning(
                ValidationStage.LINTER,
                "SHELL_LINT_ERROR",
                f"Shell linting error: {e}",
                RiskLevel.REVIEW
            )
            return True


class AppleScriptLinter:
    """AppleScript safety analysis."""
    
    def __init__(self):
        # Dangerous AppleScript commands
        self.dangerous_commands = {
            "do shell script", "system events", "system preferences",
            "keychain access", "security", "authorization",
            "mount volume", "unmount", "eject"
        }
    
    def lint_applescript(self, code: str, result: ValidationResult) -> bool:
        """Lint AppleScript for security issues."""
        try:
            code_lower = code.lower()
            
            for cmd in self.dangerous_commands:
                if cmd in code_lower:
                    if cmd == "do shell script":
                        result.add_error(
                            ValidationStage.LINTER,
                            "APPLESCRIPT_SHELL_EXEC",
                            f"AppleScript shell execution detected: {cmd}",
                            RiskLevel.BLOCKED
                        )
                        return False
                    else:
                        result.add_warning(
                            ValidationStage.LINTER,
                            "APPLESCRIPT_DANGEROUS_COMMAND",
                            f"Potentially dangerous AppleScript command: {cmd}",
                            RiskLevel.CONFIRM
                        )
            
            return True
            
        except Exception as e:
            result.add_warning(
                ValidationStage.LINTER,
                "APPLESCRIPT_LINT_ERROR",
                f"AppleScript linting error: {e}",
                RiskLevel.REVIEW
            )
            return True


class CodeLinter:
    """
    Unified code linter for the validation wall.
    Third tier - analyzes code content for dangerous operations.
    """
    
    def __init__(self):
        self.python_linter = PythonCodeLinter()
        self.shell_linter = ShellCodeLinter()
        self.applescript_linter = AppleScriptLinter()
        
        logger.info("🛡️ Code linter initialized")
    
    def lint_tool_call(self, tool_call: Dict[str, Any], result: ValidationResult) -> bool:
        """
        Lint tool call for dangerous code patterns.
        Returns True if safe, False if dangerous code detected.
        """
        tool_name = tool_call.get("tool", "")
        args = tool_call.get("args", {})
        
        try:
            # Tool-specific code analysis
            if tool_name == "write_file":
                return self._lint_file_content(args, result)
            
            elif tool_name == "macos_control":
                return self._lint_macos_commands(args, result)
            
            elif tool_name == "calculate":
                return self._lint_expression(args, result)
            
            elif tool_name in ["search_web", "web.scrape", "web.deep_research"]:
                return self._lint_web_content(args, result)
            
            # Most tools don't contain executable code
            return True
            
        except Exception as e:
            result.add_warning(
                ValidationStage.LINTER,
                "LINTER_ERROR",
                f"Code linting error: {str(e)}",
                RiskLevel.REVIEW
            )
            return True
    
    def _lint_file_content(self, args: Dict[str, Any], result: ValidationResult) -> bool:
        """Lint file content being written."""
        content = args.get("content", "")
        path = args.get("path", "")
        
        # Determine file type from path
        path_lower = path.lower()
        
        if path_lower.endswith(('.py', '.pyw')):
            return self.python_linter.lint_python_code(content, result)
        
        elif path_lower.endswith(('.sh', '.bash', '.zsh')):
            return self.shell_linter.lint_shell_code(content, result)
        
        elif path_lower.endswith('.scpt'):
            return self.applescript_linter.lint_applescript(content, result)
        
        # General content checks
        return self._lint_general_content(content, result)
    
    def _lint_macos_commands(self, args: Dict[str, Any], result: ValidationResult) -> bool:
        """Lint macOS control commands."""
        action = args.get("action", "")
        script = args.get("script", "")
        command = args.get("command", "")
        
        # AppleScript analysis
        if script:
            return self.applescript_linter.lint_applescript(script, result)
        
        # Shell command analysis
        if command:
            return self.shell_linter.lint_shell_code(command, result)
        
        return True
    
    def _lint_expression(self, args: Dict[str, Any], result: ValidationResult) -> bool:
        """Lint mathematical expressions."""
        expression = args.get("expression", "")
        
        # Check for Python code injection in math expressions
        dangerous_patterns = [
            r"__\w+__",     # Dunder methods
            r"import\s+\w+", # Import statements
            r"exec\s*\(",   # exec() calls
            r"eval\s*\(",   # eval() calls
            r"open\s*\(",   # file operations
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, expression, re.IGNORECASE):
                result.add_error(
                    ValidationStage.LINTER,
                    "EXPRESSION_CODE_INJECTION",
                    f"Potential code injection in expression: {expression}",
                    RiskLevel.BLOCKED
                )
                return False
        
        return True
    
    def _lint_web_content(self, args: Dict[str, Any], result: ValidationResult) -> bool:
        """Lint web-related arguments."""
        query = args.get("query", "")
        url = args.get("url", "")
        
        # Check for injection attempts in web queries
        injection_patterns = [
            r"<script[^>]*>",   # Script tags
            r"javascript:",     # JavaScript URLs
            r"data:text/html",  # Data URLs
            r"vbscript:",       # VBScript URLs
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, query + url, re.IGNORECASE):
                result.add_warning(
                    ValidationStage.LINTER,
                    "WEB_INJECTION_ATTEMPT",
                    f"Potential web injection detected",
                    RiskLevel.CONFIRM
                )
        
        return True
    
    def _lint_general_content(self, content: str, result: ValidationResult) -> bool:
        """General content security checks."""
        # Check for common malicious patterns
        malicious_patterns = [
            r"password\s*=\s*['\"][^'\"]+['\"]",  # Hardcoded passwords
            r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]",  # API keys
            r"secret\s*=\s*['\"][^'\"]+['\"]",    # Secrets
            r"token\s*=\s*['\"][^'\"]+['\"]",     # Tokens
        ]
        
        for pattern in malicious_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                result.add_warning(
                    ValidationStage.LINTER,
                    "SENSITIVE_DATA_DETECTED",
                    "Potential sensitive data in content",
                    RiskLevel.CONFIRM
                )
        
        return True
