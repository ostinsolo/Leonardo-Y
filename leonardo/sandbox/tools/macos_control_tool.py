#!/usr/bin/env python3
"""
macOS Control Tool - Basic macOS automation and control
Handles system commands and basic automation tasks
"""

import subprocess
import platform
from typing import Dict, Any
from .base_tool import BaseTool


class MacOSControlTool(BaseTool):
    """Tool for basic macOS system control."""
    
    async def _setup(self) -> None:
        """Check if we're running on macOS."""
        if platform.system() != "Darwin":
            self.logger.warning("⚠️ macOS Control Tool running on non-macOS system")
    
    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Execute macOS control tool."""
        
        if tool_name == "macos_control":
            return await self._execute_macos_command(args)
        elif tool_name == "send_email":
            return await self._send_email(args)
        else:
            raise ValueError(f"Unknown macOS tool: {tool_name}")
    
    async def _execute_macos_command(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute basic macOS system commands."""
        action = args.get("action", "")
        
        if action == "get_apps":
            return await self._get_running_apps()
        elif action == "system_volume":
            level = args.get("level", 50)  
            return await self._set_system_volume(level)
        elif action == "notification":
            return await self._send_notification(args)
        else:
            return {
                "action": action,
                "status": "not_implemented",
                "message": f"macOS action '{action}' not yet implemented"
            }
    
    async def _get_running_apps(self) -> Dict[str, Any]:
        """Get list of running applications."""
        try:
            if platform.system() == "Darwin":
                # Use AppleScript to get running apps
                script = '''
                tell application "System Events"
                    set appList to name of every process whose background only is false
                end tell
                return appList
                '''
                
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    apps = result.stdout.strip().split(", ")
                    return {
                        "apps": apps,
                        "count": len(apps),
                        "summary": f"Found {len(apps)} running applications"
                    }
                else:
                    raise subprocess.CalledProcessError(result.returncode, "osascript")
            else:
                return {
                    "apps": [],
                    "count": 0,
                    "summary": "Not running on macOS - cannot get application list"
                }
                
        except Exception as e:
            return {
                "error": str(e),
                "summary": f"Failed to get running applications: {e}"
            }
    
    async def _set_system_volume(self, level: int) -> Dict[str, Any]:
        """Set system volume level."""
        try:
            level = max(0, min(100, level))  # Clamp to 0-100
            
            if platform.system() == "Darwin":
                # Use AppleScript to set volume
                script = f'set volume output volume {level}'
                
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    return {
                        "level": level,
                        "summary": f"Set system volume to {level}%"
                    }
                else:
                    raise subprocess.CalledProcessError(result.returncode, "osascript")
            else:
                return {
                    "level": level,
                    "summary": f"Volume control not available on {platform.system()}"
                }
                
        except Exception as e:
            return {
                "error": str(e),
                "summary": f"Failed to set volume: {e}"
            }
    
    async def _send_notification(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Send system notification."""
        title = args.get("title", "Leonardo")
        message = args.get("message", "")
        
        try:
            if platform.system() == "Darwin":
                # Use AppleScript to send notification
                script = f'''
                display notification "{message}" with title "{title}"
                '''
                
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    return {
                        "title": title,
                        "message": message,
                        "summary": f"Sent notification: {title}"
                    }
                else:
                    raise subprocess.CalledProcessError(result.returncode, "osascript")
            else:
                return {
                    "title": title,
                    "message": message,
                    "summary": f"Notification sent (simulated on {platform.system()})"
                }
                
        except Exception as e:
            return {
                "error": str(e),
                "summary": f"Failed to send notification: {e}"
            }
    
    async def _send_email(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Send email using macOS Mail."""
        recipient = args.get("recipient", "")
        subject = args.get("subject", "")
        body = args.get("body", "")
        
        try:
            if platform.system() == "Darwin":
                # Use AppleScript to compose email
                script = f'''
                tell application "Mail"
                    set newMessage to make new outgoing message with properties {{subject:"{subject}", content:"{body}"}}
                    tell newMessage
                        make new to recipient at end of to recipients with properties {{address:"{recipient}"}}
                    end tell
                    send newMessage
                end tell
                '''
                
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                
                if result.returncode == 0:
                    return {
                        "recipient": recipient,
                        "subject": subject,
                        "summary": f"Email sent to {recipient}"
                    }
                else:
                    raise subprocess.CalledProcessError(result.returncode, "osascript")
            else:
                return {
                    "recipient": recipient,
                    "subject": subject,
                    "summary": f"Email sending not available on {platform.system()}"
                }
                
        except Exception as e:
            return {
                "error": str(e),
                "summary": f"Failed to send email: {e}"
            }
    
    async def _validate_args(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Validate macOS control arguments."""
        
        if tool_name == "macos_control":
            action = args.get("action", "")
            if not action:
                return "Action must be specified"
                
            if action == "system_volume":
                level = args.get("level", 50)
                if not isinstance(level, int) or level < 0 or level > 100:
                    return "Volume level must be an integer between 0 and 100"
        
        elif tool_name == "send_email":
            recipient = args.get("recipient", "")
            if not recipient:
                return "Email recipient must be specified"
        
        return None  # Valid
