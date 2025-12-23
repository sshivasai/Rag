"""
Vector Database Service using ChromaDB and Sentence Transformers
Handles document embeddings, storage, and similarity search
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Optional
import logging
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class VectorService:
    """Service for managing vector embeddings and similarity search"""
    
    def __init__(
        self, 
        collection_name: str = "documents",
        persist_directory: str = None,
        embedding_model: str = None
    ):
        """
        Initialize ChromaDB and embedding model
        
        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory to persist the database
            embedding_model: Name of the sentence-transformers model
        """
        # Configuration from environment
        self.persist_directory = persist_directory or os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
        self.embedding_model_name = embedding_model or os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        
        logger.info(f"Initializing VectorService with model: {self.embedding_model_name}")
        
        # Initialize ChromaDB client
        try:
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            logger.info(f"ChromaDB initialized at: {self.persist_directory}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
        
        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer(self.embedding_model_name)
            logger.info(f"Embedding model loaded: {self.embedding_model_name}")
            logger.info(f"Embedding dimension: {self.embedding_model.get_sentence_embedding_dimension()}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
        
        # Get or create collection
        try:
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )
            logger.info(f"Collection '{collection_name}' ready. Current count: {self.collection.count()}")
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            raise
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings for a list of texts
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            logger.info(f"Creating embeddings for {len(texts)} texts")
            embeddings = self.embedding_model.encode(texts, show_progress_bar=False)
            
            # Convert to list of lists
            embeddings_list = [embedding.tolist() for embedding in embeddings]
            
            logger.info(f"Created {len(embeddings_list)} embeddings")
            return embeddings_list
            
        except Exception as e:
            logger.error(f"Failed to create embeddings: {e}")
            raise
    
    def add_documents(
        self, 
        document_id: str, 
        chunks: List[str], 
        metadata: Dict
    ) -> int:
        """
        Add document chunks to the vector database
        
        Args:
            document_id: Unique identifier for the document
            chunks: List of text chunks from the document
            metadata: Metadata about the document (filename, upload date, etc.)
            
        Returns:
            Number of chunks added
        """
        try:
            logger.info(f"Adding document {document_id} with {len(chunks)} chunks")
            
            if not chunks:
                logger.warning("No chunks to add")
                return 0
            
            # Generate unique IDs for each chunk
            chunk_ids = [f"{document_id}_chunk_{idx}" for idx in range(len(chunks))]
            
            # Create embeddings for all chunks
            embeddings = self.create_embeddings(chunks)
            
            # Prepare metadata for each chunk
            metadatas = []
            for idx in range(len(chunks)):
                chunk_metadata = {
                    "document_id": document_id,
                    "chunk_index": idx,
                    "chunk_count": len(chunks),
                    "filename": metadata.get("filename", ""),
                    "uploaded_at": metadata.get("uploaded_at", ""),
                }
                metadatas.append(chunk_metadata)
            
            # Add to collection
            self.collection.add(
                ids=chunk_ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=chunks
            )
            
            logger.info(f"Successfully added {len(chunks)} chunks for document {document_id}")
            return len(chunks)
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise
    
    def search(
        self, 
        query: str, 
        top_k: int = 5, 
        min_similarity: float = 0.0,
        filter_metadata: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Search for similar documents using semantic similarity
        
        Args:
            query: Search query text
            top_k: Number of top results to return
            min_similarity: Minimum similarity threshold (0-1)
            filter_metadata: Optional metadata filters
            
        Returns:
            List of search results with content, metadata, and similarity scores
        """
        try:
            logger.info(f"Searching for: '{query[:50]}...' (top_k={top_k})")
            
            # Check if collection is empty
            if self.collection.count() == 0:
                logger.warning("Collection is empty, no results to return")
                return []
            
            # Create query embedding
            query_embedding = self.create_embeddings([query])[0]
            
            # Prepare query parameters
            query_params = {
                "query_embeddings": [query_embedding],
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"]
            }
            
            # Add metadata filter if provided
            if filter_metadata:
                query_params["where"] = filter_metadata
            
            # Search collection
            results = self.collection.query(**query_params)
            
            # Format results
            formatted_results = []
            
            if results['ids'] and len(results['ids'][0]) > 0:
                for idx in range(len(results['ids'][0])):
                    # Convert distance to similarity (1 - distance for cosine)
                    distance = results['distances'][0][idx]
                    similarity = 1 - distance
                    
                    # Filter by minimum similarity
                    if similarity >= min_similarity:
                        result = {
                            "chunk_id": results['ids'][0][idx],
                            "document_id": results['metadatas'][0][idx].get('document_id'),
                            "content": results['documents'][0][idx],
                            "metadata": results['metadatas'][0][idx],
                            "similarity": round(similarity, 4),
                            "distance": round(distance, 4)
                        }
                        formatted_results.append(result)
                
                logger.info(f"Found {len(formatted_results)} results above similarity threshold")
            else:
                logger.info("No results found")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def delete_document(self, document_id: str) -> int:
        """
        Delete all chunks of a document from the vector database
        
        Args:
            document_id: ID of the document to delete
            
        Returns:
            Number of chunks deleted
        """
        try:
            logger.info(f"Deleting document: {document_id}")
            
            # Get all chunks for this document
            results = self.collection.get(
                where={"document_id": document_id}
            )
            
            if results['ids']:
                # Delete all chunks
                self.collection.delete(ids=results['ids'])
                count = len(results['ids'])
                logger.info(f"Deleted {count} chunks for document {document_id}")
                return count
            else:
                logger.warning(f"No chunks found for document {document_id}")
                return 0
                
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            raise
    
    def get_document_chunks(self, document_id: str) -> List[Dict]:
        """
        Get all chunks for a specific document
        
        Args:
            document_id: ID of the document
            
        Returns:
            List of chunks with their content and metadata
        """
        try:
            results = self.collection.get(
                where={"document_id": document_id}
            )
            
            chunks = []
            if results['ids']:
                for idx in range(len(results['ids'])):
                    chunk = {
                        "chunk_id": results['ids'][idx],
                        "content": results['documents'][idx],
                        "metadata": results['metadatas'][idx]
                    }
                    chunks.append(chunk)
            
            logger.info(f"Retrieved {len(chunks)} chunks for document {document_id}")
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to get document chunks: {e}")
            raise
    
    def get_collection_stats(self) -> Dict:
        """
        Get statistics about the collection
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.collection.count()
            
            # Get sample to analyze
            sample = self.collection.peek(limit=10) if count > 0 else None
            
            unique_documents = set()
            if sample and sample['metadatas']:
                for metadata in sample['metadatas']:
                    if 'document_id' in metadata:
                        unique_documents.add(metadata['document_id'])
            
            stats = {
                "total_chunks": count,
                "sample_unique_documents": len(unique_documents),
                "collection_name": self.collection.name,
                "embedding_model": self.embedding_model_name,
                "embedding_dimension": self.embedding_model.get_sentence_embedding_dimension(),
                "persist_directory": self.persist_directory
            }
            
            logger.info(f"Collection stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise
    
    def clear_collection(self):
        """
        Clear all data from the collection (use with caution!)
        """
        try:
            logger.warning("Clearing entire collection!")
            
            # Get all IDs
            results = self.collection.get()
            
            if results['ids']:
                # Delete all
                self.collection.delete(ids=results['ids'])
                logger.info(f"Cleared {len(results['ids'])} items from collection")
            else:
                logger.info("Collection was already empty")
                
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            raise


# Utility function for easy initialization
def get_vector_service() -> VectorService:
    """
    Factory function to get a VectorService instance
    
    Returns:
        Initialized VectorService instance
    """
    return VectorService()