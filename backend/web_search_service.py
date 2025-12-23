"""
Web Search Service using Google Custom Search API
Handles web search and content extraction
"""

import os
import requests
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class WebSearchService:
    """Service for performing web searches"""
    
    def __init__(
        self,
        api_key: str = None,
        cse_id: str = None
    ):
        """
        Initialize Google Custom Search service
        
        Args:
            api_key: Google API key
            cse_id: Custom Search Engine ID
        """
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.cse_id = cse_id or os.getenv("GOOGLE_CSE_ID")
        
        if not self.api_key or not self.cse_id:
            logger.warning("Google Search API credentials not configured")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("✅ Google Search service initialized")
    
    def search(self, query: str, num_results: int = 3) -> List[Dict]:
        """
        Perform a Google search
        
        Args:
            query: Search query
            num_results: Number of results to return (max 10)
            
        Returns:
            List of search results
        """
        if not self.enabled:
            logger.warning("Google Search not enabled")
            return []
        
        try:
            logger.info(f"Searching Google for: '{query}'")
            
            # Google Custom Search API endpoint
            url = "https://www.googleapis.com/customsearch/v1"
            
            params = {
                "key": self.api_key,
                "cx": self.cse_id,
                "q": query,
                "num": min(num_results, 10)  # Max 10 per request
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse results
            results = []
            for item in data.get("items", []):
                result = {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "content": item.get("snippet", "")  # Initial content is snippet
                }
                results.append(result)
            
            logger.info(f"Found {len(results)} search results")
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Google Search API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def fetch_content(self, url: str, max_chars: int = 3000) -> Optional[str]:
        """
        Fetch and extract main content from a URL
        
        Args:
            url: URL to fetch
            max_chars: Maximum characters to extract
            
        Returns:
            Extracted text content or None
        """
        try:
            logger.info(f"Fetching content from: {url}")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                element.decompose()
            
            # Try to find main content
            main_content = None
            
            # Try common content containers
            for selector in ['article', 'main', '[role="main"]', '.content', '#content', '.post-content']:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            # Fallback to body
            if not main_content:
                main_content = soup.find('body')
            
            if main_content:
                # Extract text
                text = main_content.get_text(separator='\n', strip=True)
                
                # Clean up whitespace
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                text = '\n'.join(lines)
                
                # Truncate if needed
                if len(text) > max_chars:
                    text = text[:max_chars] + "..."
                
                logger.info(f"Extracted {len(text)} characters from {url}")
                return text
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to fetch content from {url}: {e}")
            return None
    
    def search_and_fetch(self, query: str, num_results: int = 3) -> List[Dict]:
        """
        Search and fetch full content from results
        
        Args:
            query: Search query
            num_results: Number of results to fetch
            
        Returns:
            List of results with full content
        """
        try:
            # Perform search
            results = self.search(query, num_results)
            
            # Fetch content for each result
            enriched_results = []
            for result in results:
                url = result.get("url", "")
                
                if url:
                    # Try to fetch full content
                    content = self.fetch_content(url)
                    
                    if content:
                        result["content"] = content
                        result["full_content"] = content
                    # If fetch fails, keep the snippet
                
                enriched_results.append(result)
            
            logger.info(f"Enriched {len(enriched_results)} results with full content")
            return enriched_results
            
        except Exception as e:
            logger.error(f"Search and fetch failed: {e}")
            return []
    
    def is_enabled(self) -> bool:
        """Check if web search is enabled"""
        return self.enabled


# Utility function
def get_web_search_service() -> WebSearchService:
    """Factory function to get WebSearchService instance"""
    return WebSearchService()