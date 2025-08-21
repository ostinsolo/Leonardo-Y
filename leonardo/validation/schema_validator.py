"""
JSON Schema Validator - First Tier of Validation Wall
Ensures all tool calls conform to exact schema requirements
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

# JSON Schema validation
try:
    import jsonschema
    from jsonschema import validate, ValidationError as JsonSchemaError
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    jsonschema = None
    JSONSCHEMA_AVAILABLE = False

from .validation_result import ValidationResult, ValidationStage, RiskLevel
from ..sandbox.tools import AVAILABLE_TOOLS

logger = logging.getLogger(__name__)


class SchemaValidator:
    """
    JSON Schema Validator for tool calls.
    First line of defense in the validation wall.
    """
    
    def __init__(self):
        self.schemas_path = Path(__file__).parent / "schemas"
        self.schemas_path.mkdir(exist_ok=True)
        
        # Load tool schemas
        self.tool_schemas = self._load_tool_schemas()
        self.available_tools = set(AVAILABLE_TOOLS.keys())
        
        logger.info(f"🛡️ Schema validator initialized with {len(self.tool_schemas)} tool schemas")
    
    def _load_tool_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Load JSON schemas for all available tools."""
        schemas = {}
        
        # Base tool call schema
        base_schema = {
            "type": "object",
            "properties": {
                "tool": {
                    "type": "string",
                    "enum": list(AVAILABLE_TOOLS.keys())
                },
                "args": {
                    "type": "object"
                },
                "meta": {
                    "type": "object",
                    "properties": {
                        "risk": {
                            "type": "string",
                            "enum": ["safe", "review", "confirm", "owner_root"]
                        },
                        "command_id": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                    },
                    "required": ["risk"]
                }
            },
            "required": ["tool", "args", "meta"]
        }
        
        # Tool-specific schemas
        tool_specific_schemas = {
            "get_weather": {
                "args": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                        "units": {"type": "string", "enum": ["metric", "imperial", "kelvin"]}
                    },
                    "required": ["location"]
                }
            },
            
            "web.deep_research": {
                "args": {
                    "type": "object", 
                    "properties": {
                        "query": {"type": "string", "minLength": 1},
                        "depth": {"type": "integer", "minimum": 1, "maximum": 5},
                        "domain_allow": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["query"]
                }
            },
            
            "read_file": {
                "args": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "minLength": 1},
                        "encoding": {"type": "string", "default": "utf-8"}
                    },
                    "required": ["path"]
                }
            },
            
            "write_file": {
                "args": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "minLength": 1},
                        "content": {"type": "string"},
                        "mode": {"type": "string", "enum": ["w", "a"], "default": "w"}
                    },
                    "required": ["path", "content"]
                }
            },
            
            "send_email": {
                "args": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "format": "email"},
                        "subject": {"type": "string", "minLength": 1},
                        "body": {"type": "string", "minLength": 1},
                        "cc": {"type": "array", "items": {"type": "string", "format": "email"}},
                        "bcc": {"type": "array", "items": {"type": "string", "format": "email"}}
                    },
                    "required": ["to", "subject", "body"]
                }
            },
            
            "calculate": {
                "args": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "minLength": 1},
                        "precision": {"type": "integer", "minimum": 1, "maximum": 50}
                    },
                    "required": ["expression"]
                }
            },
            
            "search_web": {
                "args": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "minLength": 1},
                        "k": {"type": "integer", "minimum": 1, "maximum": 20},
                        "freshness_days": {"type": "integer", "minimum": 1}
                    },
                    "required": ["query"]
                }
            },
            
            "respond": {
                "args": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "minLength": 1},
                        "type": {"type": "string", "enum": ["conversational", "informational", "error"]}
                    },
                    "required": ["message"]
                }
            }
        }
        
        # Combine base schema with tool-specific schemas
        for tool_name in AVAILABLE_TOOLS.keys():
            schema = json.loads(json.dumps(base_schema))  # Deep copy
            
            if tool_name in tool_specific_schemas:
                # Override args schema for specific tools
                schema["properties"]["args"] = tool_specific_schemas[tool_name]["args"]
            else:
                # Default: args can be any object for tools without specific schemas
                schema["properties"]["args"] = {"type": "object", "additionalProperties": True}
            
            schemas[tool_name] = schema
        
        return schemas
    
    def validate_tool_call(self, tool_call: Dict[str, Any], result: ValidationResult) -> bool:
        """
        Validate tool call against JSON schema.
        Returns True if valid, False if invalid.
        Updates ValidationResult with errors.
        """
        if not JSONSCHEMA_AVAILABLE:
            result.add_warning(
                ValidationStage.SCHEMA,
                "JSONSCHEMA_UNAVAILABLE", 
                "jsonschema library not available, skipping schema validation",
                RiskLevel.REVIEW
            )
            return True
        
        try:
            # Basic structure validation
            if not isinstance(tool_call, dict):
                result.add_error(
                    ValidationStage.SCHEMA,
                    "INVALID_TYPE",
                    f"Tool call must be dict, got {type(tool_call).__name__}",
                    RiskLevel.BLOCKED
                )
                return False
            
            # Required fields check
            required_fields = ["tool", "args", "meta"]
            missing_fields = [field for field in required_fields if field not in tool_call]
            if missing_fields:
                result.add_error(
                    ValidationStage.SCHEMA,
                    "MISSING_FIELDS",
                    f"Missing required fields: {missing_fields}",
                    RiskLevel.BLOCKED
                )
                return False
            
            tool_name = tool_call.get("tool", "")
            
            # Tool availability check
            if tool_name not in self.available_tools:
                result.add_error(
                    ValidationStage.SCHEMA,
                    "INVALID_TOOL",
                    f"Tool '{tool_name}' not found. Available: {sorted(self.available_tools)}",
                    RiskLevel.BLOCKED
                )
                return False
            
            # Schema validation
            tool_schema = self.tool_schemas.get(tool_name)
            if not tool_schema:
                result.add_warning(
                    ValidationStage.SCHEMA,
                    "NO_SCHEMA",
                    f"No schema defined for tool '{tool_name}'",
                    RiskLevel.REVIEW
                )
                return True
            
            # Validate against schema
            try:
                validate(instance=tool_call, schema=tool_schema)
                logger.debug(f"✅ Schema validation passed for {tool_name}")
                return True
                
            except JsonSchemaError as e:
                result.add_error(
                    ValidationStage.SCHEMA,
                    "SCHEMA_VIOLATION",
                    f"Schema validation failed: {e.message}",
                    RiskLevel.BLOCKED,
                    schema_path=list(e.absolute_path),
                    invalid_value=e.instance
                )
                return False
            
        except Exception as e:
            result.add_error(
                ValidationStage.SCHEMA,
                "VALIDATION_ERROR",
                f"Schema validation error: {str(e)}",
                RiskLevel.BLOCKED
            )
            return False
    
    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get schema for a specific tool."""
        return self.tool_schemas.get(tool_name)
    
    def get_available_tools(self) -> List[str]:
        """Get list of tools with schemas."""
        return list(self.tool_schemas.keys())
    
    def validate_args_only(self, tool_name: str, args: Dict[str, Any]) -> List[str]:
        """Validate only the args portion of a tool call. Returns list of errors."""
        if tool_name not in self.tool_schemas:
            return [f"No schema for tool '{tool_name}'"]
        
        if not JSONSCHEMA_AVAILABLE:
            return ["jsonschema library not available"]
        
        schema = self.tool_schemas[tool_name]
        args_schema = schema.get("properties", {}).get("args", {})
        
        try:
            validate(instance=args, schema=args_schema)
            return []
        except JsonSchemaError as e:
            return [f"Args validation failed: {e.message}"]
        except Exception as e:
            return [f"Args validation error: {str(e)}"]
