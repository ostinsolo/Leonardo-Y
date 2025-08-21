#!/usr/bin/env python3
"""
System Info Tool - Provides time, date, system information, and device status
Very commonly requested by users for basic information needs
"""

import platform
import psutil
import socket
from datetime import datetime, timezone
from typing import Dict, Any
from .base_tool import BaseTool


class SystemInfoTool(BaseTool):
    """Tool for system information, time, and date queries."""
    
    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Execute system information tool."""
        
        if tool_name == "get_time":
            return self._get_current_time(args)
        elif tool_name == "get_date":
            return self._get_current_date(args)
        elif tool_name == "system_info":
            return self._get_system_info(args)
        else:
            raise ValueError(f"Unknown system tool: {tool_name}")
    
    def _get_current_time(self, args: Dict[str, Any]) -> str:
        """Get current time with optional formatting."""
        format_type = args.get("format", "12hour")
        timezone_name = args.get("timezone", "local")
        include_seconds = args.get("include_seconds", False)
        
        try:
            # Get current time
            if timezone_name == "local":
                now = datetime.now()
                tz_info = "local time"
            elif timezone_name == "utc":
                now = datetime.now(timezone.utc)
                tz_info = "UTC"
            else:
                # Default to local if timezone not supported
                now = datetime.now()
                tz_info = "local time"
            
            # Format time based on preference
            if format_type == "24hour":
                if include_seconds:
                    time_str = now.strftime("%H:%M:%S")
                else:
                    time_str = now.strftime("%H:%M")
            else:  # 12hour format (default)
                if include_seconds:
                    time_str = now.strftime("%I:%M:%S %p")
                else:
                    time_str = now.strftime("%I:%M %p")
                    
                # Remove leading zero from 12-hour format
                if time_str.startswith("0"):
                    time_str = time_str[1:]
            
            return f"The current time is {time_str} ({tz_info})"
            
        except Exception as e:
            self.logger.error(f"Error getting time: {e}")
            # Fallback to simple format
            now = datetime.now()
            return f"The current time is {now.strftime('%I:%M %p')}"
    
    def _get_current_date(self, args: Dict[str, Any]) -> str:
        """Get current date with optional formatting."""
        format_type = args.get("format", "full")
        include_day_name = args.get("include_day_name", True)
        
        try:
            now = datetime.now()
            
            if format_type == "short":
                # MM/DD/YYYY format
                date_str = now.strftime("%m/%d/%Y")
                if include_day_name:
                    day_name = now.strftime("%A")
                    return f"Today is {day_name}, {date_str}"
                else:
                    return f"Today's date is {date_str}"
                    
            elif format_type == "iso":
                # ISO format YYYY-MM-DD
                date_str = now.strftime("%Y-%m-%d")
                if include_day_name:
                    day_name = now.strftime("%A")
                    return f"Today is {day_name}, {date_str}"
                else:
                    return f"Today's date is {date_str}"
                    
            else:  # full format (default)
                # Full format: Monday, January 15, 2024
                if include_day_name:
                    date_str = now.strftime("%A, %B %d, %Y")
                    return f"Today is {date_str}"
                else:
                    date_str = now.strftime("%B %d, %Y")
                    return f"Today's date is {date_str}"
                    
        except Exception as e:
            self.logger.error(f"Error getting date: {e}")
            # Fallback to simple format
            now = datetime.now()
            return f"Today is {now.strftime('%A, %B %d, %Y')}"
    
    def _get_system_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive system information."""
        info_type = args.get("type", "basic")
        
        try:
            system_info = {}
            
            # Basic system information (always included)
            system_info["basic"] = {
                "system": platform.system(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
                "hostname": socket.gethostname()
            }
            
            # Add macOS specific information
            if platform.system() == "Darwin":
                system_info["basic"]["macos_version"] = platform.mac_ver()[0]
            
            if info_type in ["detailed", "all"]:
                # Memory information
                memory = psutil.virtual_memory()
                system_info["memory"] = {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_percent": memory.percent,
                    "free_gb": round(memory.free / (1024**3), 2)
                }
                
                # CPU information
                system_info["cpu"] = {
                    "cores": psutil.cpu_count(),
                    "current_usage": psutil.cpu_percent(interval=1),
                    "cpu_freq": psutil.cpu_freq().current if psutil.cpu_freq() else "Unknown"
                }
                
                # Disk information
                disk = psutil.disk_usage('/')
                system_info["disk"] = {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "used_percent": round((disk.used / disk.total) * 100, 1)
                }
            
            if info_type == "all":
                # Network information
                try:
                    hostname = socket.gethostname()
                    local_ip = socket.gethostbyname(hostname)
                    system_info["network"] = {
                        "hostname": hostname,
                        "local_ip": local_ip
                    }
                except:
                    system_info["network"] = {"status": "Unable to get network info"}
                
                # Boot time
                try:
                    boot_time = datetime.fromtimestamp(psutil.boot_time())
                    system_info["boot_time"] = boot_time.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    system_info["boot_time"] = "Unknown"
            
            return system_info
            
        except Exception as e:
            self.logger.error(f"Error getting system info: {e}")
            return {
                "error": f"Unable to get system information: {e}",
                "basic": {
                    "system": platform.system(),
                    "python_version": platform.python_version()
                }
            }
    
    async def _validate_args(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Validate system info tool arguments."""
        
        if tool_name == "get_time":
            format_type = args.get("format", "12hour")
            if format_type not in ["12hour", "24hour"]:
                return "Time format must be '12hour' or '24hour'"
                
            timezone_name = args.get("timezone", "local")
            if timezone_name not in ["local", "utc"]:
                return "Timezone must be 'local' or 'utc'"
        
        elif tool_name == "get_date":
            format_type = args.get("format", "full")
            if format_type not in ["full", "short", "iso"]:
                return "Date format must be 'full', 'short', or 'iso'"
        
        elif tool_name == "system_info":
            info_type = args.get("type", "basic")
            if info_type not in ["basic", "detailed", "all"]:
                return "Info type must be 'basic', 'detailed', or 'all'"
        
        return None  # Valid
