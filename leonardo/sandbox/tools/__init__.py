"""
Leonardo's Real Tool Suite
Comprehensive collection of functional tools for real-world tasks
"""

from .base_tool import BaseTool, ToolResult
from .weather_tool import WeatherTool  
from .web_search_tool import WebSearchTool  # Legacy API-based search
from .browser_web_search_tool import BrowserWebSearchTool  # Modern browser-based search
from .crawl4ai_web_tool import Crawl4AIWebTool  # Professional web crawler (Crawl4AI)
from .deepsearcher_tool import DeepSearcherTool  # Agentic research (DeepSearcher by Zilliz)
from .file_operations_tool import FileOperationsTool
from .system_info_tool import SystemInfoTool
from .macos_control_tool import MacOSControlTool
from .calculator_tool import CalculatorTool
from .response_tool import ResponseTool
from .memory_tool import MemoryTool

# Tool registry for easy access
AVAILABLE_TOOLS = {
    "get_weather": WeatherTool,
    # Web tools (upgraded to Crawl4AI)
    "web.scrape": Crawl4AIWebTool,       # Professional web scraping (MCP contract)
    "web.search": Crawl4AIWebTool,       # Web search via Crawl4AI
    "web.extract": Crawl4AIWebTool,      # Intelligent content extraction
    "web.crawl": Crawl4AIWebTool,        # Multi-page crawling
    # Agentic research tools (DeepSearcher by Zilliz)
    "web.deep_research": DeepSearcherTool,  # PRIMARY: Agentic multi-step research (MCP)
    "research.query": DeepSearcherTool,     # Agentic research queries
    "research.add_knowledge": DeepSearcherTool,  # Add knowledge to research DB
    "research.configure": DeepSearcherTool,      # Configure research settings
    # Legacy web tools (kept for compatibility)
    "search_web": BrowserWebSearchTool,  # Legacy: Browser-based search
    "search_web_api": WebSearchTool,     # Legacy: API search as fallback
    "navigate_to": BrowserWebSearchTool, # Legacy: Browser navigation
    "interact_with_page": BrowserWebSearchTool,  # Legacy: Page interaction
    "extract_content": BrowserWebSearchTool,     # Legacy: Content extraction
    # Other tools
    "read_file": FileOperationsTool,
    "write_file": FileOperationsTool,
    "list_files": FileOperationsTool,
    "get_time": SystemInfoTool,
    "get_date": SystemInfoTool,
    "system_info": SystemInfoTool,
    "macos_control": MacOSControlTool,
    "calculate": CalculatorTool,
    "respond": ResponseTool,
    "recall_memory": MemoryTool,
    "send_email": MacOSControlTool,  # Uses macOS Mail
}

__all__ = [
    'BaseTool',
    'ToolResult', 
    'WeatherTool',
    'WebSearchTool',
    'BrowserWebSearchTool',  # Browser-based search
    'Crawl4AIWebTool',       # Professional web crawler (Crawl4AI)
    'DeepSearcherTool',      # NEW - Agentic research (DeepSearcher by Zilliz)
    'FileOperationsTool',
    'SystemInfoTool', 
    'MacOSControlTool',
    'CalculatorTool',
    'ResponseTool',
    'MemoryTool',
    'AVAILABLE_TOOLS'
]
