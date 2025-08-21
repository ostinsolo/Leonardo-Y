#!/usr/bin/env python3
"""
Calculator Tool - Performs mathematical calculations and operations  
Commonly requested for arithmetic, conversions, and mathematical functions
"""

import math
import re
from typing import Dict, Any, Union
from .base_tool import BaseTool


class CalculatorTool(BaseTool):
    """Tool for mathematical calculations and operations."""
    
    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Execute calculator tool."""
        
        if tool_name == "calculate":
            return self._calculate_expression(args)
        elif tool_name == "convert_units":
            return self._convert_units(args)
        else:
            raise ValueError(f"Unknown calculator tool: {tool_name}")
    
    def _calculate_expression(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate a mathematical expression."""
        expression = args.get("expression", "").strip()
        
        if not expression:
            raise ValueError("No expression provided")
        
        try:
            # Clean and validate the expression
            cleaned_expr = self._clean_expression(expression)
            
            # Evaluate safely
            result = self._safe_eval(cleaned_expr)
            
            # Format the result
            formatted_result = self._format_number(result)
            
            return {
                "expression": expression,
                "result": result,
                "formatted_result": formatted_result,
                "summary": f"{expression} = {formatted_result}"
            }
            
        except Exception as e:
            raise ValueError(f"Calculation error: {e}")
    
    def _convert_units(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Convert between different units."""
        value = args.get("value", 0)
        from_unit = args.get("from_unit", "").lower().strip()
        to_unit = args.get("to_unit", "").lower().strip()
        
        try:
            # Convert the value
            converted_value = self._perform_unit_conversion(value, from_unit, to_unit)
            
            # Format results
            formatted_original = self._format_number(value)
            formatted_converted = self._format_number(converted_value)
            
            return {
                "original_value": value,
                "converted_value": converted_value,
                "from_unit": from_unit,
                "to_unit": to_unit,
                "summary": f"{formatted_original} {from_unit} = {formatted_converted} {to_unit}"
            }
            
        except Exception as e:
            raise ValueError(f"Unit conversion error: {e}")
    
    def _clean_expression(self, expression: str) -> str:
        """Clean and prepare expression for safe evaluation."""
        # Remove spaces
        expr = expression.replace(" ", "")
        
        # Replace common mathematical notation
        replacements = {
            "×": "*",
            "÷": "/",
            "^": "**",
            "π": "math.pi",
            "pi": "math.pi",
            "e": "math.e",
            "√": "math.sqrt",
            "sqrt": "math.sqrt",
            "sin": "math.sin",
            "cos": "math.cos", 
            "tan": "math.tan",
            "log": "math.log10",
            "ln": "math.log",
            "abs": "abs",
            "round": "round"
        }
        
        for old, new in replacements.items():
            expr = expr.replace(old, new)
        
        # Validate characters (only allow safe mathematical operations)
        allowed_chars = set("0123456789+-*/.()mathsincogtanlogbqrpie")
        if not all(c.lower() in allowed_chars for c in expr):
            raise ValueError("Invalid characters in expression")
        
        return expr
    
    def _safe_eval(self, expression: str) -> float:
        """Safely evaluate mathematical expression."""
        # Define allowed names for evaluation
        allowed_names = {
            "__builtins__": {},
            "math": math,
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum
        }
        
        try:
            # Evaluate with restricted namespace
            result = eval(expression, allowed_names)
            
            # Ensure result is a number
            if isinstance(result, (int, float)):
                return float(result)
            else:
                raise ValueError("Result is not a number")
                
        except ZeroDivisionError:
            raise ValueError("Division by zero")
        except OverflowError:
            raise ValueError("Number too large")
        except ValueError as e:
            raise e
        except Exception:
            raise ValueError("Invalid mathematical expression")
    
    def _perform_unit_conversion(self, value: float, from_unit: str, to_unit: str) -> float:
        """Perform unit conversion between different measurement systems."""
        
        # Temperature conversions
        if from_unit in ["celsius", "c"] and to_unit in ["fahrenheit", "f"]:
            return (value * 9/5) + 32
        elif from_unit in ["fahrenheit", "f"] and to_unit in ["celsius", "c"]:
            return (value - 32) * 5/9
        elif from_unit in ["celsius", "c"] and to_unit in ["kelvin", "k"]:
            return value + 273.15
        elif from_unit in ["kelvin", "k"] and to_unit in ["celsius", "c"]:
            return value - 273.15
        elif from_unit in ["fahrenheit", "f"] and to_unit in ["kelvin", "k"]:
            return ((value - 32) * 5/9) + 273.15
        elif from_unit in ["kelvin", "k"] and to_unit in ["fahrenheit", "f"]:
            return ((value - 273.15) * 9/5) + 32
        
        # Length conversions (to meters as base)
        length_to_meters = {
            "mm": 0.001, "millimeter": 0.001, "millimeters": 0.001,
            "cm": 0.01, "centimeter": 0.01, "centimeters": 0.01,
            "m": 1.0, "meter": 1.0, "meters": 1.0,
            "km": 1000.0, "kilometer": 1000.0, "kilometers": 1000.0,
            "in": 0.0254, "inch": 0.0254, "inches": 0.0254,
            "ft": 0.3048, "foot": 0.3048, "feet": 0.3048,
            "yd": 0.9144, "yard": 0.9144, "yards": 0.9144,
            "mi": 1609.34, "mile": 1609.34, "miles": 1609.34
        }
        
        if from_unit in length_to_meters and to_unit in length_to_meters:
            meters = value * length_to_meters[from_unit]
            return meters / length_to_meters[to_unit]
        
        # Weight conversions (to grams as base)
        weight_to_grams = {
            "mg": 0.001, "milligram": 0.001, "milligrams": 0.001,
            "g": 1.0, "gram": 1.0, "grams": 1.0,
            "kg": 1000.0, "kilogram": 1000.0, "kilograms": 1000.0,
            "oz": 28.3495, "ounce": 28.3495, "ounces": 28.3495,
            "lb": 453.592, "pound": 453.592, "pounds": 453.592
        }
        
        if from_unit in weight_to_grams and to_unit in weight_to_grams:
            grams = value * weight_to_grams[from_unit]
            return grams / weight_to_grams[to_unit]
        
        # Volume conversions (to liters as base)
        volume_to_liters = {
            "ml": 0.001, "milliliter": 0.001, "milliliters": 0.001,
            "l": 1.0, "liter": 1.0, "liters": 1.0,
            "cup": 0.236588, "cups": 0.236588,
            "pt": 0.473176, "pint": 0.473176, "pints": 0.473176,
            "qt": 0.946353, "quart": 0.946353, "quarts": 0.946353,
            "gal": 3.78541, "gallon": 3.78541, "gallons": 3.78541,
            "floz": 0.0295735, "fluid_ounce": 0.0295735, "fluid_ounces": 0.0295735
        }
        
        if from_unit in volume_to_liters and to_unit in volume_to_liters:
            liters = value * volume_to_liters[from_unit]
            return liters / volume_to_liters[to_unit]
        
        # Time conversions (to seconds as base)
        time_to_seconds = {
            "s": 1.0, "second": 1.0, "seconds": 1.0,
            "min": 60.0, "minute": 60.0, "minutes": 60.0,
            "h": 3600.0, "hour": 3600.0, "hours": 3600.0,
            "d": 86400.0, "day": 86400.0, "days": 86400.0,
            "week": 604800.0, "weeks": 604800.0,
            "month": 2629746.0, "months": 2629746.0,  # Average month
            "year": 31556952.0, "years": 31556952.0   # Average year
        }
        
        if from_unit in time_to_seconds and to_unit in time_to_seconds:
            seconds = value * time_to_seconds[from_unit]
            return seconds / time_to_seconds[to_unit]
        
        raise ValueError(f"Unsupported conversion from {from_unit} to {to_unit}")
    
    def _format_number(self, number: float) -> str:
        """Format number for display."""
        # Handle very large or very small numbers
        if abs(number) >= 1e10 or (abs(number) <= 1e-4 and number != 0):
            return f"{number:.6e}"
        
        # Handle integers
        if number == int(number):
            return str(int(number))
        
        # Handle decimals
        formatted = f"{number:.10f}".rstrip('0').rstrip('.')
        return formatted if formatted else "0"
    
    async def _validate_args(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Validate calculator tool arguments."""
        
        if tool_name == "calculate":
            expression = args.get("expression", "")
            if not expression or not isinstance(expression, str):
                return "Expression must be a non-empty string"
            
            if len(expression) > 1000:
                return "Expression too long (max 1000 characters)"
        
        elif tool_name == "convert_units":
            value = args.get("value")
            if not isinstance(value, (int, float)):
                return "Value must be a number"
            
            from_unit = args.get("from_unit", "")
            to_unit = args.get("to_unit", "")
            
            if not from_unit or not isinstance(from_unit, str):
                return "from_unit must be a non-empty string"
            
            if not to_unit or not isinstance(to_unit, str):
                return "to_unit must be a non-empty string"
        
        return None  # Valid
