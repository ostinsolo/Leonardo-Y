#!/usr/bin/env python3
"""
File Operations Tool - Basic file system operations
Handles reading, writing, and listing files safely
"""

import os
from pathlib import Path
from typing import Dict, Any, List
from .base_tool import BaseTool


class FileOperationsTool(BaseTool):
    """Tool for basic file system operations."""
    
    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Execute file operations tool."""
        
        if tool_name == "read_file":
            return await self._read_file(args)
        elif tool_name == "write_file":
            return await self._write_file(args)
        elif tool_name == "list_files":
            return await self._list_files(args)
        else:
            raise ValueError(f"Unknown file tool: {tool_name}")
    
    async def _read_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Read content from a file."""
        file_path = args.get("path", "")
        max_size = args.get("max_size", 1000000)  # 1MB limit
        
        try:
            path_obj = self._safe_file_path(file_path)
            
            if not path_obj.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if not path_obj.is_file():
                raise ValueError(f"Path is not a file: {file_path}")
            
            # Check file size
            file_size = path_obj.stat().st_size
            if file_size > max_size:
                raise ValueError(f"File too large: {file_size} bytes (max: {max_size})")
            
            # Read file content
            with open(path_obj, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "path": str(path_obj),
                "content": content,
                "size": file_size,
                "lines": len(content.splitlines()),
                "summary": f"Read {file_size} bytes from {path_obj.name}"
            }
            
        except Exception as e:
            raise ValueError(f"Failed to read file '{file_path}': {e}")
    
    async def _write_file(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Write content to a file."""
        file_path = args.get("path", "")
        content = args.get("content", "")
        mode = args.get("mode", "w")  # 'w' or 'a' (write or append)
        
        try:
            path_obj = self._safe_file_path(file_path)
            
            # Create directory if it doesn't exist
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(path_obj, mode, encoding='utf-8') as f:
                f.write(content)
            
            file_size = path_obj.stat().st_size
            
            return {
                "path": str(path_obj),
                "size": file_size,
                "mode": mode,
                "summary": f"{'Wrote' if mode == 'w' else 'Appended'} {len(content)} characters to {path_obj.name}"
            }
            
        except Exception as e:
            raise ValueError(f"Failed to write file '{file_path}': {e}")
    
    async def _list_files(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List files in a directory."""
        dir_path = args.get("path", ".")
        show_hidden = args.get("show_hidden", False)
        max_files = args.get("max_files", 100)
        
        try:
            path_obj = self._safe_file_path(dir_path)
            
            if not path_obj.exists():
                raise FileNotFoundError(f"Directory not found: {dir_path}")
            
            if not path_obj.is_dir():
                raise ValueError(f"Path is not a directory: {dir_path}")
            
            # List directory contents
            files = []
            dirs = []
            
            for item in path_obj.iterdir():
                if not show_hidden and item.name.startswith('.'):
                    continue
                
                if len(files) + len(dirs) >= max_files:
                    break
                
                if item.is_file():
                    files.append({
                        "name": item.name,
                        "size": item.stat().st_size,
                        "type": "file"
                    })
                elif item.is_dir():
                    dirs.append({
                        "name": item.name,
                        "type": "directory"
                    })
            
            return {
                "path": str(path_obj),
                "files": files,
                "directories": dirs,
                "total_files": len(files),
                "total_directories": len(dirs),
                "summary": f"Found {len(files)} files and {len(dirs)} directories in {path_obj.name}"
            }
            
        except Exception as e:
            raise ValueError(f"Failed to list directory '{dir_path}': {e}")
    
    async def _validate_args(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Validate file operations arguments."""
        
        if tool_name in ["read_file", "write_file", "list_files"]:
            path = args.get("path", "")
            if not path or not isinstance(path, str):
                return "Path must be a non-empty string"
        
        if tool_name == "write_file":
            content = args.get("content", "")
            if not isinstance(content, str):
                return "Content must be a string"
            
            mode = args.get("mode", "w")
            if mode not in ["w", "a"]:
                return "Mode must be 'w' (write) or 'a' (append)"
        
        return None  # Valid
