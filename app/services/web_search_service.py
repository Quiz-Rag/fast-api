"""
Web search service using Tavily Search API.
Provides web search functionality for network security topics when ChromaDB context is insufficient.
"""

import logging
from typing import Dict, List, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class WebSearchService:
    """Service for performing web searches using Tavily API."""
    
    # Network security related keywords
    NS_KEYWORDS = [
        'encryption', 'decryption', 'cipher', 'cryptography', 'hash', 'authentication', 'authorization',
        'firewall', 'intrusion', 'malware', 'virus', 'trojan', 'worm', 'ransomware',
        'ssl', 'tls', 'https', 'http', 'tcp', 'udp', 'ip', 'dns', 'dhcp',
        'vpn', 'proxy', 'tor', 'anonymity',
        'sql injection', 'xss', 'csrf', 'ddos', 'dos', 'mitm', 'phishing',
        'rsa', 'aes', 'des', 'sha', 'md5', 'hmac', 'pki', 'certificate',
        'network security', 'cyber security', 'information security', 'data security',
        'access control', 'identity management', 'zero trust', 'defense in depth',
        'penetration testing', 'vulnerability', 'exploit', 'patch', 'update',
        'security policy', 'risk assessment', 'threat modeling', 'incident response'
    ]
    
    def __init__(self):
        """Initialize web search service."""
        if not settings.tavily_api_key:
            logger.warning("Tavily API key not configured. Web search will not be available.")
            self.tavily_client = None
        else:
            try:
                from tavily import TavilyClient
                self.tavily_client = TavilyClient(api_key=settings.tavily_api_key)
                logger.info("Tavily web search service initialized")
            except ImportError:
                logger.error("tavily-python package not installed. Install with: pip install tavily-python")
                self.tavily_client = None
            except Exception as e:
                logger.error(f"Failed to initialize Tavily client: {e}")
                self.tavily_client = None
    
    def is_network_security_related(self, question: str) -> bool:
        """
        Check if a question is related to network security.
        
        Args:
            question: User's question text
            
        Returns:
            True if question appears to be network security related
        """
        question_lower = question.lower()
        
        # Check for network security keywords
        for keyword in self.NS_KEYWORDS:
            if keyword in question_lower:
                return True
        
        # Check for common security patterns
        security_patterns = [
            'security', 'secure', 'attack', 'defense', 'protect', 'breach',
            'hack', 'hacker', 'cyber', 'network', 'protocol', 'packet'
        ]
        
        for pattern in security_patterns:
            if pattern in question_lower:
                return True
        
        return False
    
    def search_web(self, question: str, max_results: int = 3) -> Dict:
        """
        Search the web using Tavily API for network security related questions.
        
        Args:
            question: Search query
            max_results: Maximum number of results to return (default: 3)
            
        Returns:
            Dictionary with 'content' (str) and 'citations' (List[Dict])
            Format: {
                "content": "formatted search results text",
                "citations": [
                    {"source": "Website Name", "url": "https://..."},
                    ...
                ]
            }
        """
        if not self.tavily_client:
            logger.warning("Tavily client not available. Cannot perform web search.")
            return {"content": "", "citations": []}
        
        if not self.is_network_security_related(question):
            logger.info(f"Question not network security related, skipping web search: {question[:100]}")
            return {"content": "", "citations": []}
        
        try:
            logger.info(f"Searching web for: {question[:100]}...")
            
            # Perform search with Tavily
            response = self.tavily_client.search(
                query=question,
                max_results=max_results,
                search_depth="advanced"  # Use advanced search for better results
            )
            
            if not response or 'results' not in response:
                logger.warning("No results from Tavily search")
                return {"content": "", "citations": []}
            
            results = response.get('results', [])
            if not results:
                logger.warning("Empty results from Tavily search")
                return {"content": "", "citations": []}
            
            # Format results
            formatted_content = []
            citations = []
            
            for i, result in enumerate(results[:max_results], 1):
                title = result.get('title', 'Unknown')
                url = result.get('url', '')
                content = result.get('content', '')
                
                # Extract website name from URL
                website_name = self._extract_website_name(url)
                
                # Format as: [Website Name]: content
                formatted_content.append(f"[{website_name}]:\n{content}")
                
                citations.append({
                    "source": website_name,
                    "url": url,
                    "title": title
                })
            
            combined_content = "\n\n".join(formatted_content)
            
            logger.info(f"Web search completed: {len(citations)} results found")
            
            return {
                "content": combined_content,
                "citations": citations
            }
            
        except Exception as e:
            logger.error(f"Error performing web search: {e}")
            return {"content": "", "citations": []}
    
    def _extract_website_name(self, url: str) -> str:
        """
        Extract website name from URL.
        
        Args:
            url: Full URL
            
        Returns:
            Website name (e.g., "example.com" from "https://www.example.com/path")
        """
        if not url:
            return "Unknown Source"
        
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Take first part of domain (e.g., "example" from "example.com")
            if '.' in domain:
                domain = domain.split('.')[0]
            
            # Capitalize first letter
            return domain.capitalize() if domain else "Unknown Source"
        except Exception:
            return "Unknown Source"

