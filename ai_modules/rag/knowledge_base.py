"""
Knowledge base implementation for ODK MCP System.
"""

import os
import json
import pickle
import shutil
from typing import Dict, List, Tuple, Union, Optional, Any
from datetime import datetime

from ..config import AI_CONFIG
from ..utils.logging import setup_logger, log_ai_event
from ..nlp.embeddings import TextEmbedder


class KnowledgeBase:
    """
    Knowledge base for storing and retrieving documents.
    
    This class provides methods to store, retrieve, and search documents
    in a knowledge base.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize the knowledge base.
        
        Args:
            config: Configuration dictionary. If None, uses the global AI_CONFIG.
        """
        self.config = config or AI_CONFIG["rag"]
        self.logger = setup_logger("knowledge_base")
        self.embedder = TextEmbedder()
        
        # Create knowledge base directory if it doesn't exist
        os.makedirs(self.config["knowledge_base_path"], exist_ok=True)
        
        # Create index directory if it doesn't exist
        os.makedirs(self.config["index_path"], exist_ok=True)
        
        # Load index if it exists
        self.index = self._load_index()
    
    def add_document(self, document: Dict) -> Dict:
        """
        Add a document to the knowledge base.
        
        Args:
            document: Document dictionary with at least 'id', 'title', and 'content' fields.
            
        Returns:
            Dictionary with status and document ID.
        """
        if not self.config["enabled"]:
            self.logger.info("RAG is disabled in configuration")
            return {"status": "disabled", "message": "RAG is disabled in configuration"}
        
        try:
            # Validate document
            if not document.get("id"):
                document["id"] = self._generate_id()
            
            if not document.get("title"):
                return {"status": "error", "message": "Document must have a title"}
            
            if not document.get("content"):
                return {"status": "error", "message": "Document must have content"}
            
            # Add metadata
            document["added_at"] = datetime.now().isoformat()
            document["updated_at"] = document["added_at"]
            
            # Save document
            document_path = os.path.join(self.config["knowledge_base_path"], f"{document['id']}.json")
            with open(document_path, 'w', encoding='utf-8') as f:
                json.dump(document, f, indent=2)
            
            # Update index
            self._index_document(document)
            
            # Save index
            self._save_index()
            
            # Log event
            log_ai_event("knowledge_base_add_document", {
                "document_id": document["id"],
                "title": document["title"]
            })
            
            return {"status": "success", "document_id": document["id"]}
        except Exception as e:
            self.logger.error(f"Error adding document: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_document(self, document_id: str) -> Optional[Dict]:
        """
        Get a document from the knowledge base.
        
        Args:
            document_id: Document ID.
            
        Returns:
            Document dictionary or None if not found.
        """
        if not self.config["enabled"]:
            self.logger.info("RAG is disabled in configuration")
            return None
        
        try:
            document_path = os.path.join(self.config["knowledge_base_path"], f"{document_id}.json")
            if not os.path.exists(document_path):
                return None
            
            with open(document_path, 'r', encoding='utf-8') as f:
                document = json.load(f)
            
            return document
        except Exception as e:
            self.logger.error(f"Error getting document: {e}")
            return None
    
    def update_document(self, document_id: str, updates: Dict) -> Dict:
        """
        Update a document in the knowledge base.
        
        Args:
            document_id: Document ID.
            updates: Dictionary with fields to update.
            
        Returns:
            Dictionary with status and document ID.
        """
        if not self.config["enabled"]:
            self.logger.info("RAG is disabled in configuration")
            return {"status": "disabled", "message": "RAG is disabled in configuration"}
        
        try:
            # Get document
            document = self.get_document(document_id)
            if not document:
                return {"status": "error", "message": f"Document {document_id} not found"}
            
            # Update fields
            for key, value in updates.items():
                if key not in ["id", "added_at"]:
                    document[key] = value
            
            # Update metadata
            document["updated_at"] = datetime.now().isoformat()
            
            # Save document
            document_path = os.path.join(self.config["knowledge_base_path"], f"{document_id}.json")
            with open(document_path, 'w', encoding='utf-8') as f:
                json.dump(document, f, indent=2)
            
            # Update index
            self._index_document(document)
            
            # Save index
            self._save_index()
            
            # Log event
            log_ai_event("knowledge_base_update_document", {
                "document_id": document_id,
                "title": document.get("title")
            })
            
            return {"status": "success", "document_id": document_id}
        except Exception as e:
            self.logger.error(f"Error updating document: {e}")
            return {"status": "error", "message": str(e)}
    
    def delete_document(self, document_id: str) -> Dict:
        """
        Delete a document from the knowledge base.
        
        Args:
            document_id: Document ID.
            
        Returns:
            Dictionary with status.
        """
        if not self.config["enabled"]:
            self.logger.info("RAG is disabled in configuration")
            return {"status": "disabled", "message": "RAG is disabled in configuration"}
        
        try:
            # Check if document exists
            document_path = os.path.join(self.config["knowledge_base_path"], f"{document_id}.json")
            if not os.path.exists(document_path):
                return {"status": "error", "message": f"Document {document_id} not found"}
            
            # Delete document
            os.remove(document_path)
            
            # Remove from index
            self._remove_from_index(document_id)
            
            # Save index
            self._save_index()
            
            # Log event
            log_ai_event("knowledge_base_delete_document", {
                "document_id": document_id
            })
            
            return {"status": "success"}
        except Exception as e:
            self.logger.error(f"Error deleting document: {e}")
            return {"status": "error", "message": str(e)}
    
    def search(self, query: str, limit: int = None) -> List[Dict]:
        """
        Search for documents in the knowledge base.
        
        Args:
            query: Search query.
            limit: Maximum number of results to return.
            
        Returns:
            List of document dictionaries.
        """
        if not self.config["enabled"]:
            self.logger.info("RAG is disabled in configuration")
            return []
        
        if not query:
            return []
        
        try:
            # Set default limit
            if limit is None:
                limit = self.config["max_results"]
            
            # Generate query embedding
            query_embedding = self.embedder.embed_text(query)
            
            # Calculate similarity with all chunks
            similarities = []
            for chunk_id, chunk_data in self.index["chunks"].items():
                chunk_embedding = chunk_data["embedding"]
                similarity = self._calculate_similarity(query_embedding, chunk_embedding)
                similarities.append((chunk_id, similarity))
            
            # Sort by similarity
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Get top results
            top_chunks = similarities[:limit]
            
            # Get documents for top chunks
            results = []
            seen_documents = set()
            
            for chunk_id, similarity in top_chunks:
                chunk_data = self.index["chunks"][chunk_id]
                document_id = chunk_data["document_id"]
                
                # Skip if document already in results
                if document_id in seen_documents:
                    continue
                
                # Get document
                document = self.get_document(document_id)
                if document:
                    # Add similarity score
                    document["similarity"] = similarity
                    
                    # Add to results
                    results.append(document)
                    seen_documents.add(document_id)
            
            # Log event
            log_ai_event("knowledge_base_search", {
                "query": query,
                "num_results": len(results)
            })
            
            return results
        except Exception as e:
            self.logger.error(f"Error searching knowledge base: {e}")
            return []
    
    def rebuild_index(self) -> Dict:
        """
        Rebuild the index for all documents in the knowledge base.
        
        Returns:
            Dictionary with status.
        """
        if not self.config["enabled"]:
            self.logger.info("RAG is disabled in configuration")
            return {"status": "disabled", "message": "RAG is disabled in configuration"}
        
        try:
            # Clear index
            self.index = {
                "documents": {},
                "chunks": {}
            }
            
            # Get all documents
            document_files = [f for f in os.listdir(self.config["knowledge_base_path"]) if f.endswith(".json")]
            
            # Index each document
            for document_file in document_files:
                document_path = os.path.join(self.config["knowledge_base_path"], document_file)
                with open(document_path, 'r', encoding='utf-8') as f:
                    document = json.load(f)
                
                self._index_document(document)
            
            # Save index
            self._save_index()
            
            # Log event
            log_ai_event("knowledge_base_rebuild_index", {
                "num_documents": len(document_files)
            })
            
            return {"status": "success", "num_documents": len(document_files)}
        except Exception as e:
            self.logger.error(f"Error rebuilding index: {e}")
            return {"status": "error", "message": str(e)}
    
    def clear(self) -> Dict:
        """
        Clear the knowledge base.
        
        Returns:
            Dictionary with status.
        """
        if not self.config["enabled"]:
            self.logger.info("RAG is disabled in configuration")
            return {"status": "disabled", "message": "RAG is disabled in configuration"}
        
        try:
            # Delete all documents
            if os.path.exists(self.config["knowledge_base_path"]):
                shutil.rmtree(self.config["knowledge_base_path"])
            
            # Recreate directory
            os.makedirs(self.config["knowledge_base_path"], exist_ok=True)
            
            # Clear index
            self.index = {
                "documents": {},
                "chunks": {}
            }
            
            # Save index
            self._save_index()
            
            # Log event
            log_ai_event("knowledge_base_clear", {})
            
            return {"status": "success"}
        except Exception as e:
            self.logger.error(f"Error clearing knowledge base: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_stats(self) -> Dict:
        """
        Get statistics about the knowledge base.
        
        Returns:
            Dictionary with statistics.
        """
        if not self.config["enabled"]:
            self.logger.info("RAG is disabled in configuration")
            return {"status": "disabled", "message": "RAG is disabled in configuration"}
        
        try:
            # Count documents
            document_files = [f for f in os.listdir(self.config["knowledge_base_path"]) if f.endswith(".json")]
            num_documents = len(document_files)
            
            # Count chunks
            num_chunks = len(self.index["chunks"])
            
            # Get total size
            total_size = 0
            for document_file in document_files:
                document_path = os.path.join(self.config["knowledge_base_path"], document_file)
                total_size += os.path.getsize(document_path)
            
            # Get index size
            index_path = os.path.join(self.config["index_path"], "index.pkl")
            index_size = os.path.getsize(index_path) if os.path.exists(index_path) else 0
            
            return {
                "status": "success",
                "num_documents": num_documents,
                "num_chunks": num_chunks,
                "total_size": total_size,
                "index_size": index_size
            }
        except Exception as e:
            self.logger.error(f"Error getting knowledge base stats: {e}")
            return {"status": "error", "message": str(e)}
    
    def _generate_id(self) -> str:
        """
        Generate a unique ID for a document.
        
        Returns:
            Unique ID.
        """
        import uuid
        return f"doc_{uuid.uuid4().hex[:8]}"
    
    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks.
        
        Args:
            text: Text to split.
            
        Returns:
            List of text chunks.
        """
        chunk_size = self.config["chunk_size"]
        chunk_overlap = self.config["chunk_overlap"]
        
        # Split text into chunks
        chunks = []
        start = 0
        
        while start < len(text):
            # Calculate end position
            end = start + chunk_size
            
            # Adjust end position to avoid splitting words
            if end < len(text):
                # Find the last space before the end
                last_space = text.rfind(" ", start, end)
                if last_space != -1:
                    end = last_space
            
            # Add chunk
            chunks.append(text[start:end])
            
            # Update start position
            start = end - chunk_overlap
            
            # Ensure progress
            if start <= 0:
                start = end
        
        return chunks
    
    def _index_document(self, document: Dict) -> None:
        """
        Index a document.
        
        Args:
            document: Document dictionary.
        """
        document_id = document["id"]
        
        # Remove old chunks for this document
        self._remove_from_index(document_id)
        
        # Add document to index
        self.index["documents"][document_id] = {
            "title": document["title"],
            "added_at": document["added_at"],
            "updated_at": document["updated_at"]
        }
        
        # Chunk document content
        content = document["content"]
        chunks = self._chunk_text(content)
        
        # Index chunks
        for i, chunk in enumerate(chunks):
            chunk_id = f"{document_id}_chunk_{i}"
            
            # Generate embedding
            embedding = self.embedder.embed_text(chunk)
            
            # Add to index
            self.index["chunks"][chunk_id] = {
                "document_id": document_id,
                "chunk_index": i,
                "text": chunk,
                "embedding": embedding
            }
    
    def _remove_from_index(self, document_id: str) -> None:
        """
        Remove a document from the index.
        
        Args:
            document_id: Document ID.
        """
        # Remove document from index
        if document_id in self.index["documents"]:
            del self.index["documents"][document_id]
        
        # Remove chunks for this document
        chunk_ids_to_remove = []
        for chunk_id, chunk_data in self.index["chunks"].items():
            if chunk_data["document_id"] == document_id:
                chunk_ids_to_remove.append(chunk_id)
        
        for chunk_id in chunk_ids_to_remove:
            del self.index["chunks"][chunk_id]
    
    def _calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector.
            embedding2: Second embedding vector.
            
        Returns:
            Similarity score.
        """
        import numpy as np
        
        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Calculate cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _load_index(self) -> Dict:
        """
        Load the index from disk.
        
        Returns:
            Index dictionary.
        """
        index_path = os.path.join(self.config["index_path"], "index.pkl")
        
        if os.path.exists(index_path):
            try:
                with open(index_path, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                self.logger.error(f"Error loading index: {e}")
        
        # Return empty index if not found or error
        return {
            "documents": {},
            "chunks": {}
        }
    
    def _save_index(self) -> None:
        """
        Save the index to disk.
        """
        index_path = os.path.join(self.config["index_path"], "index.pkl")
        
        try:
            with open(index_path, 'wb') as f:
                pickle.dump(self.index, f)
        except Exception as e:
            self.logger.error(f"Error saving index: {e}")

