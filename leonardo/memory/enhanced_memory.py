#!/usr/bin/env python3
"""
JARVIS-1 Inspired Enhanced Memory System
Advanced memory capabilities with semantic search, clustering, and growing memory

Key JARVIS-1 Concepts Implemented:
1. Growing vs Fixed Memory (dynamic expansion)
2. Semantic Memory Clustering 
3. Experience-based Learning Storage
4. Multimodal Memory Architecture
5. Memory-Augmented Planning
"""

import asyncio
import logging
import time
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict

try:
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer
    import faiss
    from sklearn.cluster import KMeans
    from sklearn.metrics.pairwise import cosine_similarity
    ADVANCED_MEMORY_AVAILABLE = True
except ImportError:
    ADVANCED_MEMORY_AVAILABLE = False


@dataclass
class MemoryExperience:
    """JARVIS-1 inspired experience storage."""
    user_id: str
    interaction_type: str
    content: str
    context: Dict[str, Any]
    timestamp: float
    success: bool
    tools_used: List[str]
    response_quality: float = 0.0
    embedding: Optional[List[float]] = None
    cluster_id: Optional[int] = None


@dataclass  
class MemoryCluster:
    """Memory cluster for organizing related experiences."""
    cluster_id: int
    centroid: List[float]
    experiences: List[str]  # Memory IDs
    theme: str
    importance_score: float
    last_accessed: float


class EnhancedMemorySystem:
    """
    JARVIS-1 Inspired Advanced Memory System.
    
    Features:
    - Semantic clustering of experiences
    - Growing memory with importance scoring
    - Multi-modal memory storage (text + context + tools)
    - Experience-based learning and retrieval
    - Dynamic memory organization
    """
    
    def __init__(self, memory_dir: Path = None, max_experiences: int = 10000):
        self.memory_dir = memory_dir or Path("leonardo_enhanced_memory")
        self.memory_dir.mkdir(exist_ok=True)
        
        self.max_experiences = max_experiences
        self.logger = logging.getLogger(__name__)
        
        # Core storage
        self.experiences: Dict[str, MemoryExperience] = {}
        self.clusters: Dict[int, MemoryCluster] = {}
        self.user_profiles: Dict[str, Dict[str, Any]] = {}
        
        # ML components
        self.embedder: Optional[SentenceTransformer] = None
        self.chroma_client = None
        self.vector_index = None
        
        # Settings
        self.embedding_model = "all-MiniLM-L6-v2"  # Fast, good quality
        self.cluster_threshold = 0.7
        self.min_cluster_size = 3
        self.importance_decay = 0.95  # Daily decay factor
        
        self.logger.info(f"🧠 Enhanced Memory System initialized (max: {max_experiences} experiences)")
    
    async def initialize(self) -> bool:
        """Initialize advanced memory components."""
        if not ADVANCED_MEMORY_AVAILABLE:
            self.logger.warning("⚠️ Advanced memory libraries not available")
            return False
        
        try:
            # Initialize sentence transformer
            self.logger.info(f"🔄 Loading embedding model: {self.embedding_model}")
            self.embedder = SentenceTransformer(self.embedding_model)
            
            # Initialize ChromaDB for semantic search
            self.chroma_client = chromadb.PersistentClient(
                path=str(self.memory_dir / "chroma_db"),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                    is_persistent=True
                )
            )
            
            # Get or create collection
            self.collection = self.chroma_client.get_or_create_collection(
                name="leonardo_experiences",
                metadata={"hnsw:space": "cosine"}
            )
            
            # Load existing data
            await self.load_memory_data()
            
            self.logger.info("✅ Enhanced memory system ready")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize enhanced memory: {e}")
            return False
    
    async def store_experience(self, 
                             user_id: str, 
                             interaction_data: Dict[str, Any],
                             success: bool = True,
                             response_quality: float = 1.0) -> str:
        """
        Store a complete interaction experience (JARVIS-1 style).
        
        Args:
            user_id: User identifier
            interaction_data: Complete interaction context
            success: Whether the interaction was successful
            response_quality: Quality score (0-1)
        
        Returns:
            experience_id: Unique identifier for the stored experience
        """
        try:
            # Create experience
            experience_id = f"{user_id}_{int(time.time() * 1000)}"
            
            # Extract content for embedding
            content_parts = []
            if "user" in interaction_data:
                content_parts.append(f"User: {interaction_data['user']}")
            if "assistant" in interaction_data:
                content_parts.append(f"Assistant: {interaction_data['assistant']}")
            
            content = "\n".join(content_parts)
            
            # Create experience object
            experience = MemoryExperience(
                user_id=user_id,
                interaction_type=interaction_data.get("response_type", "conversation"),
                content=content,
                context=interaction_data,
                timestamp=time.time(),
                success=success,
                tools_used=interaction_data.get("tools_used", []),
                response_quality=response_quality
            )
            
            # Generate semantic embedding
            if self.embedder:
                embedding = self.embedder.encode(content).tolist()
                experience.embedding = embedding
                
                # Store in ChromaDB for semantic search
                self.collection.add(
                    documents=[content],
                    embeddings=[embedding],
                    metadatas=[{
                        "user_id": user_id,
                        "interaction_type": experience.interaction_type,
                        "timestamp": experience.timestamp,
                        "success": success,
                        "tools_used": ",".join(experience.tools_used)
                    }],
                    ids=[experience_id]
                )
            
            # Store experience
            self.experiences[experience_id] = experience
            
            # Update clusters
            await self.update_memory_clusters(experience_id, experience)
            
            # Update user profile
            self.update_user_profile(user_id, experience)
            
            # Manage memory size
            if len(self.experiences) > self.max_experiences:
                await self.prune_memory()
            
            # Save to disk
            await self.save_memory_data()
            
            self.logger.debug(f"🧠 Stored experience {experience_id} for {user_id}")
            return experience_id
            
        except Exception as e:
            self.logger.error(f"❌ Failed to store experience: {e}")
            return ""
    
    async def semantic_search(self, 
                            user_id: str, 
                            query: str, 
                            limit: int = 5,
                            min_similarity: float = 0.7) -> List[Dict[str, Any]]:
        """
        JARVIS-1 style semantic memory search.
        
        Args:
            user_id: User to search for
            query: Search query
            limit: Maximum results
            min_similarity: Minimum similarity threshold
        
        Returns:
            List of relevant experiences with similarity scores
        """
        try:
            if not self.collection or not self.embedder:
                return []
            
            # Generate query embedding
            query_embedding = self.embedder.encode(query).tolist()
            
            # Search in ChromaDB (ensure n_results is at least 1)
            n_results = max(1, limit * 2) if limit > 0 else 1
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where={"user_id": user_id}
            )
            
            # Process results
            relevant_experiences = []
            for i, (doc_id, distance) in enumerate(zip(results['ids'][0], results['distances'][0])):
                similarity = 1 - distance  # ChromaDB returns cosine distance
                
                if similarity >= min_similarity and doc_id in self.experiences:
                    experience = self.experiences[doc_id]
                    relevant_experiences.append({
                        "experience_id": doc_id,
                        "content": experience.content,
                        "context": experience.context,
                        "similarity": similarity,
                        "timestamp": experience.timestamp,
                        "tools_used": experience.tools_used,
                        "success": experience.success,
                        "cluster_id": experience.cluster_id
                    })
            
            # Sort by similarity and limit
            relevant_experiences.sort(key=lambda x: x["similarity"], reverse=True)
            return relevant_experiences[:limit]
            
        except Exception as e:
            self.logger.error(f"❌ Semantic search failed: {e}")
            return []
    
    async def get_growing_context(self, 
                                user_id: str, 
                                query: str, 
                                max_recent: int = 8,
                                max_semantic: int = 5) -> Dict[str, Any]:
        """
        JARVIS-1 inspired growing memory context retrieval.
        
        Combines:
        1. Recent experiences (chronological)
        2. Semantically relevant experiences
        3. User profile and preferences
        4. Memory clusters and themes
        """
        try:
            # Get recent experiences
            user_experiences = [
                exp for exp in self.experiences.values() 
                if exp.user_id == user_id
            ]
            recent_experiences = sorted(
                user_experiences, 
                key=lambda x: x.timestamp, 
                reverse=True
            )[:max_recent]
            
            # Get semantically relevant experiences (only if requested)
            semantic_results = []
            if max_semantic > 0 and query.strip():
                semantic_results = await self.semantic_search(
                    user_id, query, limit=max_semantic
                )
            
            # Get user profile
            user_profile = self.user_profiles.get(user_id, {})
            
            # Get active clusters
            user_clusters = self.get_user_clusters(user_id)
            
            # Format for Leonardo compatibility (recent_turns format)
            recent_turns = []
            for exp in recent_experiences:
                if "user" in exp.context and "assistant" in exp.context:
                    recent_turns.append({
                        "user_input": exp.context["user"],
                        "ai_response": exp.context["assistant"],
                        "timestamp": exp.timestamp,
                        "success": exp.success,
                        "tools_used": exp.tools_used,
                        "experience_id": list(self.experiences.keys())[list(self.experiences.values()).index(exp)]
                    })
            
            return {
                "recent_turns": recent_turns,
                "relevant_memories": semantic_results,
                "user_profile": user_profile,
                "memory_clusters": user_clusters,
                "memory_stats": {
                    "total_experiences": len(user_experiences),
                    "successful_interactions": sum(1 for e in user_experiences if e.success),
                    "memory_themes": len(user_clusters),
                    "backend_type": "enhanced_jarvis",
                    "growing_memory": True
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get growing context: {e}")
            return {"recent_turns": [], "relevant_memories": [], "user_profile": {}}
    
    async def update_memory_clusters(self, experience_id: str, experience: MemoryExperience):
        """Update memory clusters based on new experience (JARVIS-1 clustering)."""
        if not experience.embedding:
            return
        
        try:
            # Find best matching cluster
            best_cluster_id = None
            best_similarity = 0.0
            
            for cluster_id, cluster in self.clusters.items():
                similarity = cosine_similarity(
                    [experience.embedding], 
                    [cluster.centroid]
                )[0][0]
                
                if similarity > best_similarity and similarity > self.cluster_threshold:
                    best_similarity = similarity
                    best_cluster_id = cluster_id
            
            if best_cluster_id:
                # Add to existing cluster
                self.clusters[best_cluster_id].experiences.append(experience_id)
                self.clusters[best_cluster_id].last_accessed = time.time()
                experience.cluster_id = best_cluster_id
            else:
                # Create new cluster
                new_cluster_id = len(self.clusters)
                cluster = MemoryCluster(
                    cluster_id=new_cluster_id,
                    centroid=experience.embedding,
                    experiences=[experience_id],
                    theme=self.extract_theme(experience.content),
                    importance_score=1.0,
                    last_accessed=time.time()
                )
                self.clusters[new_cluster_id] = cluster
                experience.cluster_id = new_cluster_id
                
        except Exception as e:
            self.logger.error(f"❌ Failed to update clusters: {e}")
    
    def extract_theme(self, content: str) -> str:
        """Extract theme from content (simplified)."""
        # Simple keyword-based theme extraction
        themes = {
            "time": ["time", "clock", "when", "date", "today", "now"],
            "weather": ["weather", "temperature", "rain", "sunny", "forecast"],
            "search": ["search", "find", "look", "google", "information"],
            "programming": ["code", "program", "python", "debug", "function"],
            "memory": ["remember", "recall", "memory", "forgot", "before"],
            "greeting": ["hello", "hi", "hey", "goodbye", "thanks"]
        }
        
        content_lower = content.lower()
        for theme, keywords in themes.items():
            if any(keyword in content_lower for keyword in keywords):
                return theme
        
        return "general"
    
    def get_user_clusters(self, user_id: str) -> List[Dict[str, Any]]:
        """Get memory clusters for a specific user."""
        user_clusters = []
        
        for cluster in self.clusters.values():
            # Check if cluster has experiences from this user
            cluster_experiences = [
                self.experiences[exp_id] for exp_id in cluster.experiences 
                if exp_id in self.experiences and self.experiences[exp_id].user_id == user_id
            ]
            
            if cluster_experiences:
                user_clusters.append({
                    "cluster_id": cluster.cluster_id,
                    "theme": cluster.theme,
                    "experience_count": len(cluster_experiences),
                    "importance_score": cluster.importance_score,
                    "last_accessed": cluster.last_accessed
                })
        
        return sorted(user_clusters, key=lambda x: x["importance_score"], reverse=True)
    
    def update_user_profile(self, user_id: str, experience: MemoryExperience):
        """Update user profile based on new experience."""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                "total_interactions": 0,
                "successful_interactions": 0,
                "preferred_tools": defaultdict(int),
                "interaction_types": defaultdict(int),
                "themes": defaultdict(int),
                "first_interaction": time.time(),
                "last_interaction": time.time()
            }
        
        profile = self.user_profiles[user_id]
        profile["total_interactions"] += 1
        profile["last_interaction"] = experience.timestamp
        
        if experience.success:
            profile["successful_interactions"] += 1
        
        # Update preferences
        for tool in experience.tools_used:
            profile["preferred_tools"][tool] += 1
        
        profile["interaction_types"][experience.interaction_type] += 1
        
        # Extract theme and update
        theme = self.extract_theme(experience.content)
        profile["themes"][theme] += 1
    
    async def prune_memory(self):
        """Prune old/unimportant memories to maintain performance."""
        try:
            # Sort experiences by importance (recency + success + cluster importance)
            scored_experiences = []
            current_time = time.time()
            
            for exp_id, experience in self.experiences.items():
                # Calculate importance score
                age_days = (current_time - experience.timestamp) / 86400
                age_score = self.importance_decay ** age_days
                success_score = 1.0 if experience.success else 0.5
                quality_score = experience.response_quality
                
                cluster_score = 1.0
                if experience.cluster_id and experience.cluster_id in self.clusters:
                    cluster_score = self.clusters[experience.cluster_id].importance_score
                
                total_score = age_score * success_score * quality_score * cluster_score
                scored_experiences.append((exp_id, total_score))
            
            # Keep top experiences
            keep_count = int(self.max_experiences * 0.8)  # Keep 80%
            scored_experiences.sort(key=lambda x: x[1], reverse=True)
            
            experiences_to_keep = set(exp_id for exp_id, _ in scored_experiences[:keep_count])
            experiences_to_remove = set(self.experiences.keys()) - experiences_to_keep
            
            # Remove from storage
            for exp_id in experiences_to_remove:
                del self.experiences[exp_id]
                
                # Remove from ChromaDB
                try:
                    self.collection.delete(ids=[exp_id])
                except:
                    pass  # May not exist in ChromaDB
            
            self.logger.info(f"🗑️ Pruned {len(experiences_to_remove)} old experiences")
            
        except Exception as e:
            self.logger.error(f"❌ Memory pruning failed: {e}")
    
    async def save_memory_data(self):
        """Save memory data to disk."""
        try:
            # Save experiences
            experiences_file = self.memory_dir / "experiences.json"
            with open(experiences_file, 'w') as f:
                json.dump({
                    exp_id: asdict(exp) for exp_id, exp in self.experiences.items()
                }, f, indent=2)
            
            # Save clusters
            clusters_file = self.memory_dir / "clusters.json"
            with open(clusters_file, 'w') as f:
                json.dump({
                    str(cluster_id): asdict(cluster) for cluster_id, cluster in self.clusters.items()
                }, f, indent=2)
            
            # Save user profiles
            profiles_file = self.memory_dir / "user_profiles.json"
            with open(profiles_file, 'w') as f:
                json.dump(dict(self.user_profiles), f, indent=2)
                
        except Exception as e:
            self.logger.error(f"❌ Failed to save memory data: {e}")
    
    async def load_memory_data(self):
        """Load memory data from disk."""
        try:
            # Load experiences
            experiences_file = self.memory_dir / "experiences.json"
            if experiences_file.exists():
                with open(experiences_file, 'r') as f:
                    data = json.load(f)
                    self.experiences = {
                        exp_id: MemoryExperience(**exp_data)
                        for exp_id, exp_data in data.items()
                    }
            
            # Load clusters
            clusters_file = self.memory_dir / "clusters.json"
            if clusters_file.exists():
                with open(clusters_file, 'r') as f:
                    data = json.load(f)
                    self.clusters = {
                        int(cluster_id): MemoryCluster(**cluster_data)
                        for cluster_id, cluster_data in data.items()
                    }
            
            # Load user profiles
            profiles_file = self.memory_dir / "user_profiles.json"
            if profiles_file.exists():
                with open(profiles_file, 'r') as f:
                    self.user_profiles = json.load(f)
            
            self.logger.info(f"📂 Loaded {len(self.experiences)} experiences, {len(self.clusters)} clusters")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load memory data: {e}")
    
    async def shutdown(self):
        """Clean shutdown of enhanced memory system."""
        await self.save_memory_data()
        self.logger.info("✅ Enhanced memory system shutdown complete")
