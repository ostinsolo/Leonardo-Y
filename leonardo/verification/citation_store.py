"""
Citation Store and RAG Cache Management
Manages normalized content, stable content IDs, and citation format

Separate from conversational memory - focused on verification/research data.
Implements the exact citation format specified for deterministic NLI.
"""

import json
import hashlib
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)


@dataclass
class ContentSpan:
    """Byte-accurate span in normalized text."""
    start: int
    end: int


@dataclass
class CitationSource:
    """Individual source backing a claim."""
    content_id: str
    url: str  
    title: str
    retrieved_at: str  # ISO timestamp
    span: ContentSpan
    quote: str  # Actual text slice
    hash: str  # SHA256 of quote for integrity


@dataclass
class ClaimCitation:
    """Citation object linking claim to sources."""
    claim_id: str
    claim_text: str
    sources: List[CitationSource]


@dataclass
class StoredContent:
    """Normalized content stored in RAG cache."""
    content_id: str
    url: str
    domain: str
    title: str
    fetched_at: str  # ISO timestamp  
    text: str  # Normalized markdown/plain text
    fingerprint: str  # SHA256 of text
    metadata: Dict[str, Any]


class CitationStore:
    """
    Citation store and RAG cache manager.
    Handles content normalization, stable IDs, and citation resolution.
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        # Separate cache directory from conversational memory
        self.cache_dir = cache_dir or Path("leonardo_verification_cache")
        self.pages_dir = self.cache_dir / "pages"
        self.index_dir = self.cache_dir / "index"
        
        # Create directory structure
        self.cache_dir.mkdir(exist_ok=True)
        self.pages_dir.mkdir(exist_ok=True)
        self.index_dir.mkdir(exist_ok=True)
        
        # URL mapping for quick lookups
        self.url_map_file = self.index_dir / "url_map.json"
        self.url_map = self._load_url_map()
        
        logger.info(f"📚 Citation store initialized: {self.cache_dir}")
        logger.info(f"   Cached pages: {len(self.url_map)}")
    
    def _load_url_map(self) -> Dict[str, str]:
        """Load URL to content_id mapping."""
        try:
            if self.url_map_file.exists():
                with open(self.url_map_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load URL map: {e}")
        
        return {}
    
    def _save_url_map(self):
        """Save URL to content_id mapping."""
        try:
            with open(self.url_map_file, 'w') as f:
                json.dump(self.url_map, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save URL map: {e}")
    
    def generate_content_id(self, url: str, title: str = "") -> str:
        """Generate stable content ID for URL."""
        # Use URL + title for more stable IDs
        content = f"{url}:{title}".encode('utf-8')
        hash_hex = hashlib.sha256(content).hexdigest()
        return f"doc_{hash_hex[:8]}"
    
    def store_content(self, url: str, title: str, text: str, metadata: Dict[str, Any] = None) -> str:
        """
        Store normalized content in RAG cache.
        
        Returns:
            content_id for the stored content
        """
        try:
            # Generate stable content ID
            content_id = self.generate_content_id(url, title)
            
            # Create domain from URL
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc.lower()
            except:
                domain = "unknown"
            
            # Create content fingerprint
            fingerprint = hashlib.sha256(text.encode('utf-8')).hexdigest()
            
            # Create stored content object
            stored_content = StoredContent(
                content_id=content_id,
                url=url,
                domain=domain,
                title=title,
                fetched_at=datetime.now().isoformat(),
                text=text,
                fingerprint=fingerprint,
                metadata=metadata or {}
            )
            
            # Save to disk
            content_file = self.pages_dir / f"{content_id}.json"
            with open(content_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(stored_content), f, indent=2, ensure_ascii=False)
            
            # Update URL mapping
            self.url_map[url] = content_id
            self._save_url_map()
            
            logger.info(f"✅ Stored content: {content_id} ({url})")
            return content_id
            
        except Exception as e:
            logger.error(f"❌ Failed to store content for {url}: {e}")
            return ""
    
    def get_content(self, content_id: str) -> Optional[StoredContent]:
        """Retrieve stored content by ID."""
        try:
            content_file = self.pages_dir / f"{content_id}.json"
            if not content_file.exists():
                return None
            
            with open(content_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return StoredContent(**data)
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve content {content_id}: {e}")
            return None
    
    def get_content_by_url(self, url: str) -> Optional[StoredContent]:
        """Retrieve stored content by URL."""
        content_id = self.url_map.get(url)
        if content_id:
            return self.get_content(content_id)
        return None
    
    def extract_span_text(self, content_id: str, span: ContentSpan) -> Optional[str]:
        """Extract text slice from stored content using byte spans."""
        try:
            stored_content = self.get_content(content_id)
            if not stored_content:
                logger.warning(f"Content {content_id} not found for span extraction")
                return None
            
            # Extract text slice using byte offsets
            text = stored_content.text
            if span.end > len(text.encode('utf-8')):
                logger.warning(f"Span {span} exceeds content length for {content_id}")
                return None
            
            # Handle UTF-8 byte slicing carefully
            text_bytes = text.encode('utf-8')
            span_bytes = text_bytes[span.start:span.end]
            span_text = span_bytes.decode('utf-8', errors='ignore')
            
            return span_text
            
        except Exception as e:
            logger.error(f"❌ Failed to extract span from {content_id}: {e}")
            return None
    
    def create_citation_source(self, content_id: str, span: ContentSpan) -> Optional[CitationSource]:
        """Create citation source from content and span."""
        try:
            stored_content = self.get_content(content_id)
            if not stored_content:
                return None
            
            # Extract quote text
            quote = self.extract_span_text(content_id, span)
            if not quote:
                return None
            
            # Generate quote hash for integrity
            quote_hash = hashlib.sha256(quote.encode('utf-8')).hexdigest()
            
            return CitationSource(
                content_id=content_id,
                url=stored_content.url,
                title=stored_content.title,
                retrieved_at=stored_content.fetched_at,
                span=span,
                quote=quote,
                hash=f"sha256:{quote_hash}"
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to create citation source: {e}")
            return None
    
    def create_claim_citation(self, claim_text: str, sources: List[Tuple[str, ContentSpan]]) -> ClaimCitation:
        """
        Create complete citation object for a claim.
        
        Args:
            claim_text: The claim being cited
            sources: List of (content_id, span) tuples
            
        Returns:
            ClaimCitation object with all sources resolved
        """
        # Generate unique claim ID
        claim_id = f"c_{uuid.uuid4().hex[:8]}"
        
        # Resolve all sources
        citation_sources = []
        for content_id, span in sources:
            citation_source = self.create_citation_source(content_id, span)
            if citation_source:
                citation_sources.append(citation_source)
        
        return ClaimCitation(
            claim_id=claim_id,
            claim_text=claim_text,
            sources=citation_sources
        )
    
    def resolve_citations(self, citations: List[ClaimCitation]) -> List[Tuple[str, List[str]]]:
        """
        Resolve citations to (claim, evidence_texts) for NLI verification.
        
        Returns:
            List of (claim_text, evidence_quotes) tuples ready for NLI
        """
        resolved = []
        
        for citation in citations:
            claim_text = citation.claim_text
            evidence_quotes = [source.quote for source in citation.sources if source.quote]
            
            resolved.append((claim_text, evidence_quotes))
        
        return resolved
    
    def verify_citation_integrity(self, citation: ClaimCitation) -> bool:
        """Verify citation source integrity using hashes."""
        try:
            for source in citation.sources:
                # Re-extract quote and check hash
                extracted_quote = self.extract_span_text(source.content_id, source.span)
                if not extracted_quote:
                    logger.warning(f"Could not extract quote for source {source.content_id}")
                    return False
                
                # Verify hash
                expected_hash = hashlib.sha256(extracted_quote.encode('utf-8')).hexdigest()
                stored_hash = source.hash.replace("sha256:", "")
                
                if expected_hash != stored_hash:
                    logger.warning(f"Hash mismatch for source {source.content_id}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Citation integrity verification failed: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            total_files = len(list(self.pages_dir.glob("*.json")))
            total_urls = len(self.url_map)
            
            # Calculate total cache size
            cache_size = 0
            for file_path in self.pages_dir.glob("*.json"):
                cache_size += file_path.stat().st_size
            
            return {
                "cache_dir": str(self.cache_dir),
                "stored_pages": total_files,
                "url_mappings": total_urls,
                "cache_size_mb": round(cache_size / (1024 * 1024), 2),
                "consistency": total_files == total_urls
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get cache stats: {e}")
            return {"error": str(e)}
    
    def cleanup_old_content(self, days_to_keep: int = 30):
        """Remove content older than specified days."""
        try:
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 60 * 60)
            removed_count = 0
            
            for content_file in self.pages_dir.glob("*.json"):
                try:
                    with open(content_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    fetched_at = datetime.fromisoformat(data.get("fetched_at", "")).timestamp()
                    if fetched_at < cutoff_date:
                        # Remove from URL map
                        url = data.get("url", "")
                        if url in self.url_map:
                            del self.url_map[url]
                        
                        # Remove file
                        content_file.unlink()
                        removed_count += 1
                        
                except Exception:
                    continue
            
            # Save updated URL map
            self._save_url_map()
            
            logger.info(f"🧹 Cleaned up {removed_count} old content files")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
