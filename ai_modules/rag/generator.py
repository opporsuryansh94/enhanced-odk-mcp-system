"""
Enhanced RAG (Retrieval-Augmented Generation) system for ODK MCP System.
Provides intelligent knowledge base and context-aware response generation.
"""

import os
import json
import pickle
import numpy as np
from typing import Dict, List, Tuple, Union, Optional, Any
from datetime import datetime
import faiss
from sentence_transformers import SentenceTransformer

from ..config import AI_CONFIG, check_subscription_limit
from ..utils.logging import setup_logger, log_ai_event


class EnhancedRAGSystem:
    """
    Enhanced RAG system that provides intelligent knowledge base management
    and context-aware response generation for the ODK MCP System.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize the enhanced RAG system.
        
        Args:
            config: Configuration dictionary. If None, uses the global AI_CONFIG.
        """
        self.config = config or AI_CONFIG["rag"]
        self.logger = setup_logger("enhanced_rag_system")
        
        # Initialize components
        self.embedding_model = None
        self.vector_store = None
        self.knowledge_base = {}
        self.document_chunks = []
        self.chunk_metadata = []
        
        # Initialize if enabled
        if self.config["enabled"]:
            self._initialize_components()
            self._load_knowledge_base()
    
    def add_documents(self, documents: List[Dict]) -> Dict:
        """
        Add documents to the knowledge base.
        
        Args:
            documents: List of documents with content and metadata.
            
        Returns:
            Dictionary with operation results.
        """
        if not self.config["enabled"]:
            return {"status": "disabled", "message": "RAG system is disabled"}
        
        try:
            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "documents_added": 0,
                "chunks_created": 0,
                "errors": []
            }
            
            for doc in documents:
                try:
                    # Process document
                    chunks = self._chunk_document(doc)
                    embeddings = self._generate_embeddings(chunks)
                    
                    # Add to vector store
                    self._add_to_vector_store(chunks, embeddings, doc)
                    
                    result["documents_added"] += 1
                    result["chunks_created"] += len(chunks)
                    
                except Exception as e:
                    error_msg = f"Error processing document {doc.get('id', 'unknown')}: {str(e)}"
                    result["errors"].append(error_msg)
                    self.logger.error(error_msg)
            
            # Save updated knowledge base
            self._save_knowledge_base()
            
            # Log event
            log_ai_event("rag_documents_added", {
                "documents_count": result["documents_added"],
                "chunks_count": result["chunks_created"]
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error adding documents to RAG system: {e}")
            return {"status": "error", "message": str(e)}
    
    def query(self, query: str, 
              context: Dict = None,
              user_plan: str = "starter",
              current_usage: int = 0,
              max_results: int = None) -> Dict:
        """
        Query the knowledge base with context-aware retrieval.
        
        Args:
            query: Query string.
            context: Additional context information.
            user_plan: User's subscription plan.
            current_usage: Current monthly usage count.
            max_results: Maximum number of results to return.
            
        Returns:
            Dictionary with query results and generated response.
        """
        if not self.config["enabled"]:
            return {"status": "disabled", "message": "RAG system is disabled"}
        
        # Check subscription limits
        if not check_subscription_limit("rag", user_plan, 
                                      "max_queries_per_month", current_usage):
            return {
                "status": "limit_exceeded",
                "message": f"Monthly RAG queries limit exceeded for {user_plan} plan"
            }
        
        try:
            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "context": context,
                "retrieved_documents": [],
                "generated_response": "",
                "confidence_score": 0.0,
                "sources": []
            }
            
            # Retrieve relevant documents
            retrieved_docs = self._retrieve_documents(query, context, max_results)
            result["retrieved_documents"] = retrieved_docs
            
            # Generate response
            if retrieved_docs:
                response = self._generate_response(query, retrieved_docs, context)
                result["generated_response"] = response["text"]
                result["confidence_score"] = response["confidence"]
                result["sources"] = response["sources"]
            else:
                result["generated_response"] = "I couldn't find relevant information to answer your query."
                result["confidence_score"] = 0.0
            
            # Log event
            log_ai_event("rag_query", {
                "user_plan": user_plan,
                "query_length": len(query),
                "retrieved_docs": len(retrieved_docs),
                "confidence": result["confidence_score"]
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing RAG query: {e}")
            return {"status": "error", "message": str(e)}
    
    def update_knowledge_base(self, updates: List[Dict]) -> Dict:
        """
        Update existing knowledge base entries.
        
        Args:
            updates: List of updates with document IDs and new content.
            
        Returns:
            Dictionary with update results.
        """
        try:
            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "updates_applied": 0,
                "errors": []
            }
            
            for update in updates:
                try:
                    doc_id = update.get("document_id")
                    new_content = update.get("content")
                    
                    if doc_id and new_content:
                        # Remove old chunks
                        self._remove_document_chunks(doc_id)
                        
                        # Add new chunks
                        doc = {"id": doc_id, "content": new_content, **update.get("metadata", {})}
                        chunks = self._chunk_document(doc)
                        embeddings = self._generate_embeddings(chunks)
                        self._add_to_vector_store(chunks, embeddings, doc)
                        
                        result["updates_applied"] += 1
                
                except Exception as e:
                    error_msg = f"Error updating document {update.get('document_id', 'unknown')}: {str(e)}"
                    result["errors"].append(error_msg)
                    self.logger.error(error_msg)
            
            # Save updated knowledge base
            self._save_knowledge_base()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error updating knowledge base: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_knowledge_base_stats(self) -> Dict:
        """
        Get statistics about the knowledge base.
        
        Returns:
            Dictionary with knowledge base statistics.
        """
        try:
            stats = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "total_documents": len(self.knowledge_base),
                "total_chunks": len(self.document_chunks),
                "vector_store_size": self.vector_store.ntotal if self.vector_store else 0,
                "embedding_dimension": self.config.get("embedding_model", "").split("/")[-1] if self.embedding_model else 0,
                "storage_info": {
                    "knowledge_base_path": self.config["knowledge_base_path"],
                    "index_path": self.config["index_path"]
                }
            }
            
            # Document type distribution
            doc_types = {}
            for doc_id, doc_data in self.knowledge_base.items():
                doc_type = doc_data.get("type", "unknown")
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            
            stats["document_types"] = doc_types
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting knowledge base stats: {e}")
            return {"status": "error", "message": str(e)}
    
    def _initialize_components(self) -> None:
        """Initialize RAG system components."""
        try:
            # Initialize embedding model
            model_name = self.config.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
            self.embedding_model = SentenceTransformer(model_name)
            
            # Initialize vector store
            embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
            self.vector_store = faiss.IndexFlatIP(embedding_dim)  # Inner product for cosine similarity
            
            self.logger.info(f"Initialized RAG system with model: {model_name}")
            
        except Exception as e:
            self.logger.error(f"Error initializing RAG components: {e}")
            raise
    
    def _chunk_document(self, document: Dict) -> List[Dict]:
        """
        Chunk a document into smaller pieces.
        
        Args:
            document: Document with content and metadata.
            
        Returns:
            List of document chunks.
        """
        content = document.get("content", "")
        chunk_size = self.config.get("chunk_size", 1000)
        chunk_overlap = self.config.get("chunk_overlap", 200)
        
        chunks = []
        
        # Simple text chunking (can be enhanced with more sophisticated methods)
        words = content.split()
        
        for i in range(0, len(words), chunk_size - chunk_overlap):
            chunk_words = words[i:i + chunk_size]
            chunk_text = " ".join(chunk_words)
            
            chunk = {
                "text": chunk_text,
                "document_id": document.get("id"),
                "chunk_index": len(chunks),
                "metadata": {
                    "title": document.get("title", ""),
                    "type": document.get("type", ""),
                    "source": document.get("source", ""),
                    "timestamp": document.get("timestamp", datetime.now().isoformat()),
                    **document.get("metadata", {})
                }
            }
            
            chunks.append(chunk)
        
        return chunks
    
    def _generate_embeddings(self, chunks: List[Dict]) -> np.ndarray:
        """
        Generate embeddings for document chunks.
        
        Args:
            chunks: List of document chunks.
            
        Returns:
            Numpy array of embeddings.
        """
        texts = [chunk["text"] for chunk in chunks]
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
        
        # Normalize for cosine similarity
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        return embeddings
    
    def _add_to_vector_store(self, chunks: List[Dict], embeddings: np.ndarray, document: Dict) -> None:
        """
        Add chunks and embeddings to the vector store.
        
        Args:
            chunks: Document chunks.
            embeddings: Chunk embeddings.
            document: Original document.
        """
        # Add embeddings to FAISS index
        self.vector_store.add(embeddings)
        
        # Store chunks and metadata
        for chunk in chunks:
            self.document_chunks.append(chunk)
            self.chunk_metadata.append({
                "document_id": document.get("id"),
                "chunk_index": chunk["chunk_index"],
                "vector_index": len(self.document_chunks) - 1
            })
        
        # Store document in knowledge base
        self.knowledge_base[document.get("id")] = {
            "title": document.get("title", ""),
            "content": document.get("content", ""),
            "type": document.get("type", ""),
            "source": document.get("source", ""),
            "timestamp": document.get("timestamp", datetime.now().isoformat()),
            "chunk_count": len(chunks),
            "metadata": document.get("metadata", {})
        }
    
    def _retrieve_documents(self, query: str, context: Dict = None, max_results: int = None) -> List[Dict]:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: Query string.
            context: Additional context.
            max_results: Maximum number of results.
            
        Returns:
            List of relevant document chunks.
        """
        if not self.document_chunks:
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)
        query_embedding = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
        
        # Search vector store
        max_results = max_results or self.config.get("max_results", 5)
        scores, indices = self.vector_store.search(query_embedding, max_results)
        
        # Retrieve and rank results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.document_chunks):
                chunk = self.document_chunks[idx].copy()
                chunk["relevance_score"] = float(score)
                results.append(chunk)
        
        # Apply reranking if enabled
        if self.config.get("reranking_enabled", True):
            results = self._rerank_results(query, results, context)
        
        return results
    
    def _rerank_results(self, query: str, results: List[Dict], context: Dict = None) -> List[Dict]:
        """
        Rerank search results based on additional criteria.
        
        Args:
            query: Original query.
            results: Initial search results.
            context: Additional context.
            
        Returns:
            Reranked results.
        """
        # Simple reranking based on multiple factors
        for result in results:
            # Base score from vector similarity
            base_score = result["relevance_score"]
            
            # Boost recent documents
            doc_timestamp = result["metadata"].get("timestamp", "")
            if doc_timestamp:
                try:
                    doc_date = datetime.fromisoformat(doc_timestamp.replace("Z", "+00:00"))
                    days_old = (datetime.now() - doc_date.replace(tzinfo=None)).days
                    recency_boost = max(0, 1 - days_old / 365)  # Boost for documents less than a year old
                    base_score += recency_boost * 0.1
                except:
                    pass
            
            # Boost based on document type relevance
            doc_type = result["metadata"].get("type", "")
            if context and "preferred_types" in context:
                if doc_type in context["preferred_types"]:
                    base_score += 0.2
            
            # Boost based on source reliability
            source = result["metadata"].get("source", "")
            reliable_sources = ["official", "documentation", "manual", "guide"]
            if any(reliable in source.lower() for reliable in reliable_sources):
                base_score += 0.1
            
            result["final_score"] = base_score
        
        # Sort by final score
        results.sort(key=lambda x: x["final_score"], reverse=True)
        
        return results
    
    def _generate_response(self, query: str, retrieved_docs: List[Dict], context: Dict = None) -> Dict:
        """
        Generate a response based on retrieved documents.
        
        Args:
            query: Original query.
            retrieved_docs: Retrieved document chunks.
            context: Additional context.
            
        Returns:
            Dictionary with generated response and metadata.
        """
        # For now, implementing a simple extractive approach
        # In a full implementation, you might use a language model for generation
        
        # Combine relevant chunks
        combined_text = ""
        sources = []
        
        for doc in retrieved_docs[:3]:  # Use top 3 most relevant
            combined_text += doc["text"] + "\n\n"
            sources.append({
                "document_id": doc["document_id"],
                "title": doc["metadata"].get("title", ""),
                "relevance_score": doc["relevance_score"]
            })
        
        # Simple response generation (extract most relevant sentences)
        sentences = combined_text.split(".")
        
        # Score sentences based on query terms
        query_terms = set(query.lower().split())
        sentence_scores = []
        
        for sentence in sentences:
            if len(sentence.strip()) < 10:  # Skip very short sentences
                continue
            
            sentence_lower = sentence.lower()
            score = sum(1 for term in query_terms if term in sentence_lower)
            sentence_scores.append((sentence.strip(), score))
        
        # Sort by score and take top sentences
        sentence_scores.sort(key=lambda x: x[1], reverse=True)
        top_sentences = [s[0] for s in sentence_scores[:3] if s[1] > 0]
        
        response_text = ". ".join(top_sentences)
        if response_text and not response_text.endswith("."):
            response_text += "."
        
        # Calculate confidence based on relevance scores
        avg_relevance = np.mean([doc["relevance_score"] for doc in retrieved_docs]) if retrieved_docs else 0
        confidence = min(avg_relevance, 1.0)
        
        return {
            "text": response_text or "I couldn't find specific information to answer your query.",
            "confidence": float(confidence),
            "sources": sources
        }
    
    def _remove_document_chunks(self, document_id: str) -> None:
        """
        Remove all chunks for a specific document.
        
        Args:
            document_id: ID of the document to remove.
        """
        # This is a simplified implementation
        # In practice, you'd need to rebuild the FAISS index or use a more sophisticated approach
        
        # Remove from knowledge base
        if document_id in self.knowledge_base:
            del self.knowledge_base[document_id]
        
        # Remove chunks (simplified - in practice, you'd rebuild the index)
        self.document_chunks = [
            chunk for chunk in self.document_chunks 
            if chunk.get("document_id") != document_id
        ]
        
        self.chunk_metadata = [
            meta for meta in self.chunk_metadata 
            if meta.get("document_id") != document_id
        ]
    
    def _load_knowledge_base(self) -> None:
        """Load knowledge base from storage."""
        kb_path = self.config["knowledge_base_path"]
        index_path = self.config["index_path"]
        
        try:
            # Load knowledge base metadata
            if os.path.exists(f"{kb_path}/knowledge_base.json"):
                with open(f"{kb_path}/knowledge_base.json", 'r') as f:
                    self.knowledge_base = json.load(f)
            
            # Load document chunks
            if os.path.exists(f"{kb_path}/document_chunks.pkl"):
                with open(f"{kb_path}/document_chunks.pkl", 'rb') as f:
                    self.document_chunks = pickle.load(f)
            
            # Load chunk metadata
            if os.path.exists(f"{kb_path}/chunk_metadata.pkl"):
                with open(f"{kb_path}/chunk_metadata.pkl", 'rb') as f:
                    self.chunk_metadata = pickle.load(f)
            
            # Load FAISS index
            if os.path.exists(f"{index_path}/faiss.index"):
                self.vector_store = faiss.read_index(f"{index_path}/faiss.index")
            
            self.logger.info(f"Loaded knowledge base with {len(self.knowledge_base)} documents")
            
        except Exception as e:
            self.logger.error(f"Error loading knowledge base: {e}")
    
    def _save_knowledge_base(self) -> None:
        """Save knowledge base to storage."""
        kb_path = self.config["knowledge_base_path"]
        index_path = self.config["index_path"]
        
        try:
            # Create directories
            os.makedirs(kb_path, exist_ok=True)
            os.makedirs(index_path, exist_ok=True)
            
            # Save knowledge base metadata
            with open(f"{kb_path}/knowledge_base.json", 'w') as f:
                json.dump(self.knowledge_base, f, indent=2)
            
            # Save document chunks
            with open(f"{kb_path}/document_chunks.pkl", 'wb') as f:
                pickle.dump(self.document_chunks, f)
            
            # Save chunk metadata
            with open(f"{kb_path}/chunk_metadata.pkl", 'wb') as f:
                pickle.dump(self.chunk_metadata, f)
            
            # Save FAISS index
            if self.vector_store:
                faiss.write_index(self.vector_store, f"{index_path}/faiss.index")
            
            self.logger.info("Saved knowledge base to storage")
            
        except Exception as e:
            self.logger.error(f"Error saving knowledge base: {e}")


# Backward compatibility
RAGSystem = EnhancedRAGSystem

