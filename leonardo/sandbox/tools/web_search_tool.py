#!/usr/bin/env python3
"""
Web Search Tool - Performs internet searches and web research
Popular feature for getting current information and answers
"""

import json
import re
from typing import Dict, Any, List
from .base_tool import BaseTool

# HTTP client imports
try:
    import aiohttp
    HTTP_CLIENT_AVAILABLE = True
except ImportError:
    HTTP_CLIENT_AVAILABLE = False

# BeautifulSoup for HTML parsing
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


class WebSearchTool(BaseTool):
    """Tool for web search and information retrieval."""
    
    def __init__(self, config):
        super().__init__(config)
        self.search_engines = {
            "duckduckgo": "https://duckduckgo.com/html/?q=",
            "bing": "https://www.bing.com/search?q=",
            "google": "https://www.google.com/search?q="
        }
        self.default_engine = "duckduckgo"  # Privacy-focused default
        
    async def _setup(self) -> None:
        """Setup web search configuration."""
        if not HTTP_CLIENT_AVAILABLE:
            self.logger.warning("⚠️ aiohttp not available - web search will use mock results")
        if not BS4_AVAILABLE:
            self.logger.warning("⚠️ BeautifulSoup not available - limited HTML parsing")
        
        # Get search engine preference from config
        preferred_engine = self._get_config_value("search.engine", self.default_engine)
        if preferred_engine in self.search_engines:
            self.default_engine = preferred_engine
    
    async def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Execute web search tool."""
        
        if tool_name == "search_web":
            return await self._search_web(args)
        elif tool_name == "get_page_content":
            return await self._get_page_content(args)
        else:
            raise ValueError(f"Unknown web search tool: {tool_name}")
    
    async def _search_web(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Search the web for information."""
        query = args.get("query", "").strip()
        max_results = min(args.get("max_results", 5), 10)  # Limit to 10 results
        engine = args.get("engine", self.default_engine)
        
        if not query:
            raise ValueError("Search query cannot be empty")
        
        try:
            if HTTP_CLIENT_AVAILABLE:
                results = await self._perform_web_search(query, max_results, engine)
            else:
                results = self._get_mock_search_results(query, max_results)
            
            return {
                "query": query,
                "engine": engine,
                "results": results,
                "count": len(results),
                "summary": self._create_search_summary(query, results)
            }
            
        except Exception as e:
            self.logger.error(f"Web search failed for '{query}': {e}")
            return {
                "query": query,
                "engine": engine,
                "results": [],
                "count": 0,
                "error": str(e),
                "summary": f"I'm sorry, I couldn't search for '{query}' right now. {e}"
            }
    
    async def _get_page_content(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get content from a specific web page."""
        url = args.get("url", "").strip()
        
        if not url:
            raise ValueError("URL cannot be empty")
        
        # Basic URL validation
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        try:
            if HTTP_CLIENT_AVAILABLE:
                content = await self._fetch_page_content(url)
            else:
                content = {"error": "HTTP client not available"}
            
            return {
                "url": url,
                "content": content
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get content from {url}: {e}")
            return {
                "url": url,
                "error": str(e),
                "summary": f"I couldn't access the webpage at {url}. {e}"
            }
    
    async def _perform_web_search(self, query: str, max_results: int, engine: str) -> List[Dict[str, Any]]:
        """Perform actual web search using specified engine."""
        if engine not in self.search_engines:
            engine = self.default_engine
        
        # For this implementation, we'll use DuckDuckGo's instant answer API
        # which is more API-friendly than scraping search results
        if engine == "duckduckgo":
            return await self._search_duckduckgo_api(query, max_results)
        else:
            # For other engines, return mock results for now
            # In production, you'd implement proper API integrations
            return self._get_mock_search_results(query, max_results)
    
    async def _search_duckduckgo_api(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo's instant answer API."""
        try:
            # DuckDuckGo Instant Answer API
            api_url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_duckduckgo_response(data, query, max_results)
                    else:
                        raise ValueError(f"API error: {response.status}")
                        
        except Exception as e:
            self.logger.error(f"DuckDuckGo API search failed: {e}")
            return self._get_mock_search_results(query, max_results)
    
    def _parse_duckduckgo_response(self, data: Dict[str, Any], query: str, max_results: int) -> List[Dict[str, Any]]:
        """Parse DuckDuckGo API response."""
        results = []
        
        # Abstract (instant answer)
        if data.get("Abstract"):
            results.append({
                "title": data.get("Heading", "Instant Answer"),
                "snippet": data["Abstract"][:300],
                "url": data.get("AbstractURL", ""),
                "source": data.get("AbstractSource", "DuckDuckGo")
            })
        
        # Related topics
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("Text", "")[:100] + "...",
                    "snippet": topic.get("Text", "")[:300],
                    "url": topic.get("FirstURL", ""),
                    "source": "DuckDuckGo Related"
                })
        
        # If no results, create a basic result
        if not results:
            results.append({
                "title": f"Search results for: {query}",
                "snippet": f"Search performed for '{query}'. You may want to try a more specific query.",
                "url": f"https://duckduckgo.com/?q={query.replace(' ', '+')}",
                "source": "DuckDuckGo"
            })
        
        return results[:max_results]
    
    async def _fetch_page_content(self, url: str) -> Dict[str, Any]:
        """Fetch content from a web page."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        if BS4_AVAILABLE:
                            return self._parse_html_content(html, url)
                        else:
                            return {
                                "title": "Page Content",
                                "text": html[:1000] + "..." if len(html) > 1000 else html,
                                "raw_html": True
                            }
                    else:
                        raise ValueError(f"HTTP {response.status}")
                        
        except Exception as e:
            raise ValueError(f"Failed to fetch page: {e}")
    
    def _parse_html_content(self, html: str, url: str) -> Dict[str, Any]:
        """Parse HTML content to extract meaningful information."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract title
            title = soup.title.string if soup.title else "No Title"
            
            # Extract main content
            text_content = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text_content.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Limit text length
            if len(text) > 2000:
                text = text[:2000] + "..."
            
            return {
                "title": title.strip(),
                "text": text,
                "url": url,
                "length": len(text)
            }
            
        except Exception as e:
            return {
                "title": "Parse Error", 
                "text": f"Could not parse content: {e}",
                "url": url,
                "error": str(e)
            }
    
    def _get_mock_search_results(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """Generate mock search results for testing/fallback."""
        mock_results = []
        
        # Generate relevant-seeming mock results
        topics = self._generate_mock_topics(query)
        
        for i, topic in enumerate(topics[:max_results]):
            mock_results.append({
                "title": f"{topic} - Information about {query}",
                "snippet": f"Learn more about {topic} related to {query}. This is mock search data for demonstration purposes.",
                "url": f"https://example.com/search/{query.replace(' ', '-')}/{i+1}",
                "source": "Mock Search Engine"
            })
        
        return mock_results
    
    def _generate_mock_topics(self, query: str) -> List[str]:
        """Generate relevant mock topics based on query."""
        query_lower = query.lower()
        
        # Common topic patterns
        if any(word in query_lower for word in ["weather", "forecast", "climate"]):
            return ["Weather Forecast", "Climate Data", "Weather Patterns", "Meteorology", "Local Weather"]
        
        elif any(word in query_lower for word in ["python", "programming", "code"]):
            return ["Python Tutorial", "Programming Guide", "Code Examples", "Python Documentation", "Development Tips"]
        
        elif any(word in query_lower for word in ["news", "current", "today"]):
            return ["Latest News", "Current Events", "Today's Headlines", "Breaking News", "News Updates"]
        
        elif any(word in query_lower for word in ["recipe", "cooking", "food"]):
            return ["Recipe Ideas", "Cooking Tips", "Food Preparation", "Culinary Guide", "Cooking Techniques"]
        
        else:
            # Generic topics
            return [
                f"{query} Overview",
                f"{query} Guide", 
                f"{query} Information",
                f"{query} Tutorial",
                f"{query} Resources"
            ]
    
    def _create_search_summary(self, query: str, results: List[Dict[str, Any]]) -> str:
        """Create a summary of search results."""
        if not results:
            return f"I couldn't find any results for '{query}'. You might want to try a different search term."
        
        summary_parts = [f"I found {len(results)} result{'s' if len(results) > 1 else ''} for '{query}':"]
        
        for i, result in enumerate(results[:3], 1):  # Summarize top 3 results
            title = result.get("title", "No Title")[:80]
            if len(result.get("title", "")) > 80:
                title += "..."
            summary_parts.append(f"{i}. {title}")
        
        if len(results) > 3:
            summary_parts.append(f"... and {len(results) - 3} more results.")
        
        return " ".join(summary_parts)
    
    async def _validate_args(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Validate web search tool arguments."""
        
        if tool_name == "search_web":
            query = args.get("query", "")
            if not query or not isinstance(query, str) or not query.strip():
                return "Search query must be a non-empty string"
            
            if len(query) > 500:
                return "Search query too long (max 500 characters)"
            
            max_results = args.get("max_results", 5)
            if not isinstance(max_results, int) or max_results < 1 or max_results > 10:
                return "max_results must be an integer between 1 and 10"
        
        elif tool_name == "get_page_content":
            url = args.get("url", "")
            if not url or not isinstance(url, str):
                return "URL must be a non-empty string"
            
            # Basic URL validation
            if not any(url.lower().startswith(prefix) for prefix in ["http://", "https://", "www.", "ftp://"]):
                return "URL must be a valid web address"
        
        return None  # Valid
