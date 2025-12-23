from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
from dotenv import load_dotenv
import logging
import uuid
import aiofiles
from pathlib import Path
from typing import Dict, Optional

# Import our services
from vector_service import VectorService
from document_processor import DocumentProcessor
from redis_service import RedisService
from llm_service import LLMService
from web_search_service import WebSearchService
from models import (
    ChatMessage,
    ChatResponse,
    Source,
    ModelInfo,
    ModelsResponse,
    DocumentUploadResponse,
    DocumentListItem,
    DocumentDeleteResponse,
    ErrorResponse
)

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="RAG Chatbot API",
    description="Retrieval-Augmented Generation chatbot with knowledge base",
    version="1.0.0"
)

# CORS Configuration
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
vector_service = None
document_processor = None
redis_service = None
llm_service = None
web_search_service = None

# In-memory document metadata storage (replace with DB in production)
documents_metadata = {}

# Temporary upload directory
UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Startup event
@app.on_event("startup")
async def startup_event():
    global vector_service, document_processor, redis_service, llm_service, web_search_service
    
    logger.info("🚀 Starting RAG Chatbot API")
    logger.info(f"📝 Log Level: {os.getenv('LOG_LEVEL', 'INFO')}")
    logger.info(f"🔧 Environment loaded: {'.env file found' if os.getenv('ANTHROPIC_API_KEY') else '⚠️  .env file missing'}")
    
    # Initialize Vector Service
    try:
        logger.info("Initializing Vector Service...")
        vector_service = VectorService()
        logger.info("✅ Vector Service initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Vector Service: {e}")
        vector_service = None
    
    # Initialize Document Processor
    try:
        logger.info("Initializing Document Processor...")
        document_processor = DocumentProcessor()
        logger.info("✅ Document Processor initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Document Processor: {e}")
        document_processor = None
    
    # Initialize Redis Service
    try:
        logger.info("Initializing Redis Service...")
        redis_service = RedisService()
        logger.info("✅ Redis Service initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Redis Service: {e}")
        logger.warning("⚠️  Continuing without Redis - sessions will not persist")
        redis_service = None
    
    # Initialize LLM Service
    try:
        logger.info("Initializing LLM Service (Claude)...")
        llm_service = LLMService()
        logger.info("✅ LLM Service initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize LLM Service: {e}")
        llm_service = None
    
    # Initialize Web Search Service
    try:
        logger.info("Initializing Web Search Service...")
        web_search_service = WebSearchService()
        if web_search_service.is_enabled():
            logger.info("✅ Web Search Service initialized successfully")
        else:
            logger.warning("⚠️  Web Search Service disabled (missing credentials)")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Web Search Service: {e}")
        web_search_service = None

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 Shutting down RAG Chatbot API")
    
    # Close Redis connection
    if redis_service:
        try:
            redis_service.close()
            logger.info("✅ Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis: {e}")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "🤖 RAG Chatbot API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "health": "/api/health",
            "chat": "/api/chat",
            "documents": "/api/documents",
            "upload": "/api/documents/upload",
            "sessions": "/api/sessions"
        }
    }

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """
    Health check endpoint to verify API is running
    and all services are configured
    """
    
    # Check environment variables
    env_status = {
        "anthropic_api": "✅" if os.getenv("ANTHROPIC_API_KEY") else "❌",
        "google_api": "✅" if os.getenv("GOOGLE_API_KEY") else "❌",
        "google_cse_id": "✅" if os.getenv("GOOGLE_CSE_ID") else "❌",
        "redis_configured": "✅" if os.getenv("REDIS_HOST") else "❌",
        "vector_service": "✅" if vector_service else "❌",
        "redis_service": "✅" if redis_service else "❌"
    }
    
    all_configured = all(status == "✅" for status in env_status.values())
    
    # Get vector database stats if available
    vector_stats = None
    if vector_service:
        try:
            vector_stats = vector_service.get_collection_stats()
        except Exception as e:
            logger.error(f"Failed to get vector stats: {e}")
    
    response = {
        "status": "healthy" if all_configured else "partially_configured",
        "timestamp": datetime.now().isoformat(),
        "environment": env_status,
        "message": "All services configured ✅" if all_configured else "⚠️  Some services need configuration"
    }
    
    if vector_stats:
        response["vector_database"] = {
            "total_chunks": vector_stats["total_chunks"],
            "embedding_model": vector_stats["embedding_model"],
            "embedding_dimension": vector_stats["embedding_dimension"]
        }
    
    # Get Redis stats if available
    if redis_service:
        try:
            redis_stats = redis_service.get_stats()
            response["redis"] = {
                "connected": redis_stats.get("connected", False),
                "active_sessions": redis_stats.get("active_sessions", 0),
                "total_messages": redis_stats.get("total_messages", 0)
            }
        except Exception as e:
            logger.error(f"Failed to get Redis stats: {e}")
            response["redis"] = {"connected": False}
    
    return response

# Test endpoint to verify API keys (without exposing them)
@app.get("/api/verify-keys")
async def verify_keys():
    """Verify API keys are loaded (for debugging only - remove in production)"""
    
    def mask_key(key: str) -> str:
        if not key:
            return "❌ Not set"
        if len(key) < 8:
            return "❌ Invalid"
        return f"✅ {key[:8]}...{key[-4:]}"
    
    return {
        "anthropic_api_key": mask_key(os.getenv("ANTHROPIC_API_KEY", "")),
        "google_api_key": mask_key(os.getenv("GOOGLE_API_KEY", "")),
        "google_cse_id": mask_key(os.getenv("GOOGLE_CSE_ID", "")),
        "redis_host": os.getenv("REDIS_HOST", "❌ Not set")
    }


# ============================================================================
# CHAT ENDPOINT - RAG with Citations
# ============================================================================

@app.post("/api/chat", response_model=ChatResponse)
async def chat(chat_request: ChatMessage):
    """
    Chat endpoint with RAG and web search capabilities
    
    Features:
    - Searches vector database for relevant documents
    - Optional web search for additional context
    - Generates response with Claude
    - Provides source citations (Perplexity-style)
    - Stores conversation in Redis
    """
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not initialized")
    
    try:
        query = chat_request.message
        session_id = chat_request.session_id
        use_web_search = chat_request.use_web_search
        model_override = chat_request.model
        use_document_search = chat_request.use_document_search

        logger.info(f"💬 Chat request: '{query[:50]}...' (web_search={use_web_search}, document_search={use_document_search}, model={model_override or 'default'})")

        # Create or validate session
        if not session_id or (redis_service and not redis_service.session_exists(session_id)):
            if redis_service:
                session_id = redis_service.generate_session_id()
                redis_service.create_session(session_id)
                logger.info(f"Created new session: {session_id}")
            else:
                # Fallback if Redis not available
                session_id = str(uuid.uuid4())
                logger.warning("Redis not available, using temporary session ID")
        
        # Get conversation history
        conversation_history = []
        if redis_service and session_id:
            try:
                conversation_history = redis_service.get_messages(session_id)
            except Exception as e:
                logger.error(f"Failed to get conversation history: {e}")
        
        # 1. Search vector database for relevant documents
        document_results = []
        if vector_service and use_document_search:
            try:
                top_k = int(os.getenv("TOP_K_RESULTS", "5"))
                min_sim = float(os.getenv("MIN_SIMILARITY", "0.5"))
                
                document_results = vector_service.search(
                    query,
                    top_k=top_k,
                    min_similarity=min_sim
                )
                logger.info(f"📚 Found {len(document_results)} relevant document chunks")
            except Exception as e:
                logger.error(f"Vector search failed: {e}")
        
        # 2. Web search if enabled and requested
        web_results = []
        if use_web_search and web_search_service and web_search_service.is_enabled():
            try:
                web_results = web_search_service.search_and_fetch(query, num_results=3)
                logger.info(f"🌐 Found {len(web_results)} web results")
            except Exception as e:
                logger.error(f"Web search failed: {e}")
        
        
        # 3. Generate response with Claude
        try:
            response_text, sources = llm_service.generate_with_search_results(
                query=query,
                document_results=document_results,
                web_results=web_results,
                conversation_history=conversation_history,
                model=model_override
            )
            
            logger.info(f"✅ Generated response with {len(sources)} sources")
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate response: {str(e)}")
        
        # 4. Store conversation in Redis
        if redis_service and session_id:
            try:
                # Store user message
                redis_service.add_message(
                    session_id,
                    role="user",
                    content=query
                )
                
                # Store assistant message
                redis_service.add_message(
                    session_id,
                    role="assistant",
                    content=response_text,
                    metadata={"sources": [s for s in sources]}
                )
                
                # Update session activity
                redis_service.update_session_activity(session_id)
                
                logger.info(f"💾 Stored conversation in session {session_id}")
                
            except Exception as e:
                logger.error(f"Failed to store conversation: {e}")
        
        # 5. Format response
        formatted_sources = [Source(**source) for source in sources]
        
        return ChatResponse(
            response=response_text,
            sources=formatted_sources,
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            model_used=model_override or llm_service.model
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Chat endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models", response_model=ModelsResponse)
async def get_available_models():
    """
    Get list of available Claude models
    
    Returns list of models that users can select from
    """
    if not llm_service:
        raise HTTPException(status_code=503, detail="LLM service not initialized")
    
    try:
        models = llm_service.get_available_models()
        
        # Format for response
        model_infos = [ModelInfo(**model) for model in models]
        
        return ModelsResponse(
            models=model_infos,
            default_model=llm_service.default_model
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# DOCUMENT ENDPOINTS
# ============================================================================

@app.post("/api/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a document
    
    Supports: .txt, .pdf, .json files
    """
    if not document_processor or not vector_service:
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    try:
        logger.info(f"📤 Upload request: {file.filename}")
        
        # Validate file
        is_valid, error_msg = document_processor.validate_file(file.filename)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Generate document ID
        doc_id = str(uuid.uuid4())
        
        # Read file content
        content = await file.read()
        
        # Save file temporarily
        file_path = UPLOAD_DIR / f"{doc_id}_{file.filename}"
        
        # Write as binary to preserve encoding
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        file_size = len(content)
        
        logger.info(f"💾 Saved temporarily: {file_path}")
        
        # Process document
        try:
            full_text, chunks, stats = document_processor.process_document(
                str(file_path),
                file.filename,
                clean=True
            )
            
            logger.info(f"✂️ Created {len(chunks)} chunks")
            
            # Store in vector database
            metadata = {
                "filename": file.filename,
                "uploaded_at": datetime.now().isoformat()
            }
            
            chunks_stored = vector_service.add_documents(doc_id, chunks, metadata)
            logger.info(f"🗄️ Stored {chunks_stored} chunks in vector DB")
            
            # Store metadata
            documents_metadata[doc_id] = {
                "id": doc_id,
                "filename": file.filename,
                "file_type": os.path.splitext(file.filename)[1],
                "file_size": file_size,
                "uploaded_at": metadata["uploaded_at"],
                "chunks_count": len(chunks),
                "word_count": stats["words"],
                "character_count": stats["characters"]
            }
            
            logger.info(f"✅ Document uploaded successfully: {doc_id}")
            
            return DocumentUploadResponse(
                document_id=doc_id,
                filename=file.filename,
                chunks_created=len(chunks),
                message="Document uploaded and processed successfully",
                stats=stats
            )
            
        finally:
            # Clean up temporary file
            if file_path.exists():
                file_path.unlink()
                logger.info(f"🧹 Cleaned up temporary file")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/api/documents", response_model=list[DocumentListItem])
async def list_documents():
    """
    Get list of all uploaded documents
    """
    try:
        documents = [
            DocumentListItem(**doc_meta)
            for doc_meta in documents_metadata.values()
        ]
        
        # Sort by upload date (newest first)
        documents.sort(key=lambda x: x.uploaded_at, reverse=True)
        
        logger.info(f"📋 Returning {len(documents)} documents")
        return documents
        
    except Exception as e:
        logger.error(f"❌ Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/documents/{document_id}")
async def get_document(document_id: str):
    """
    Get details of a specific document
    """
    if document_id not in documents_metadata:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        # Get metadata
        metadata = documents_metadata[document_id]
        
        # Get chunks from vector DB
        chunks = vector_service.get_document_chunks(document_id)
        
        return {
            "metadata": metadata,
            "chunks": chunks,
            "total_chunks": len(chunks)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/documents/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(document_id: str):
    """
    Delete a document and all its chunks
    """
    if document_id not in documents_metadata:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not vector_service:
        raise HTTPException(status_code=503, detail="Vector service not available")
    
    try:
        filename = documents_metadata[document_id]["filename"]
        
        # Delete from vector database
        chunks_deleted = vector_service.delete_document(document_id)
        logger.info(f"🗑️ Deleted {chunks_deleted} chunks from vector DB")
        
        # Delete metadata
        del documents_metadata[document_id]
        
        logger.info(f"✅ Document deleted: {document_id}")
        
        return DocumentDeleteResponse(
            message="Document deleted successfully",
            document_id=document_id,
            filename=filename,
            chunks_deleted=chunks_deleted
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SESSION MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/api/sessions/create")
async def create_session(metadata: Optional[Dict] = None):
    """
    Create a new chat session
    
    Returns session_id and TTL information
    """
    if not redis_service:
        raise HTTPException(status_code=503, detail="Redis service not available")
    
    try:
        session_id = redis_service.generate_session_id()
        success = redis_service.create_session(session_id, metadata)
        
        if success:
            logger.info(f"✅ Created session: {session_id}")
            return {
                "session_id": session_id,
                "message": "Session created successfully",
                "ttl": redis_service.session_ttl,
                "created_at": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create session")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}")
async def get_session_info(session_id: str):
    """
    Get session information and conversation history
    """
    if not redis_service:
        raise HTTPException(status_code=503, detail="Redis service not available")
    
    try:
        # Check if session exists
        if not redis_service.session_exists(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get session data
        session_data = redis_service.get_session(session_id)
        
        # Get messages
        messages = redis_service.get_messages(session_id)
        
        logger.info(f"📖 Retrieved session {session_id} with {len(messages)} messages")
        
        return {
            "session": session_data,
            "messages": messages,
            "total_messages": len(messages)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session and all its messages
    """
    if not redis_service:
        raise HTTPException(status_code=503, detail="Redis service not available")
    
    try:
        if not redis_service.session_exists(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        success = redis_service.delete_session(session_id)
        
        if success:
            logger.info(f"🗑️ Deleted session: {session_id}")
            return {
                "message": "Session deleted successfully",
                "session_id": session_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to delete session")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions")
async def list_sessions():
    """
    List all active sessions
    """
    if not redis_service:
        raise HTTPException(status_code=503, detail="Redis service not available")
    
    try:
        session_ids = redis_service.get_all_sessions()
        
        sessions = []
        for sid in session_ids:
            session_data = redis_service.get_session(sid)
            if session_data:
                sessions.append({
                    "session_id": sid,
                    "created_at": session_data.get("created_at"),
                    "message_count": session_data.get("message_count", 0),
                    "last_activity": session_data.get("last_activity")
                })
        
        logger.info(f"📋 Returning {len(sessions)} active sessions")
        
        return {
            "sessions": sessions,
            "total": len(sessions)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to list sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sessions/{session_id}/clear")
async def clear_session_messages(session_id: str):
    """
    Clear all messages in a session (keep session alive)
    """
    if not redis_service:
        raise HTTPException(status_code=503, detail="Redis service not available")
    
    try:
        if not redis_service.session_exists(session_id):
            raise HTTPException(status_code=404, detail="Session not found")
        
        success = redis_service.clear_messages(session_id)
        
        if success:
            logger.info(f"🧹 Cleared messages for session: {session_id}")
            return {
                "message": "Messages cleared successfully",
                "session_id": session_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to clear messages")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to clear messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    
    logger.info(f"🌐 Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port, reload=True)