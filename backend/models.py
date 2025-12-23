"""
Pydantic models for API request/response validation
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


# Chat Models
class ChatMessage(BaseModel):
    """Chat message request"""
    message: str = Field(..., min_length=1, max_length=5000, description="User message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    use_web_search: bool = Field(False, description="Enable web search fallback")
    use_document_search: Optional[bool] = Field(False, description="Enable document search")
    model: Optional[str] = Field(None, description="Override default Claude model (e.g., 'claude-sonnet-4-20250514')")


class Source(BaseModel):
    """Source citation"""
    type: str = Field(..., description="Source type: 'document' or 'web'")
    source_number: int = Field(..., description="Source number for citation")
    title: Optional[str] = Field(None, description="Title (for web sources)")
    filename: Optional[str] = Field(None, description="Filename (for document sources)")
    url: Optional[str] = Field(None, description="URL (for web sources)")
    similarity: Optional[float] = Field(None, description="Similarity score (for document sources)")
    preview: str = Field(..., description="Content preview")


class ChatResponse(BaseModel):
    """Chat message response"""
    response: str = Field(..., description="AI assistant response")
    sources: List[Source] = Field(default_factory=list, description="Source citations")
    session_id: str = Field(..., description="Session ID")
    timestamp: str = Field(..., description="Response timestamp")
    model_used: Optional[str] = Field(None, description="Model that generated the response")


# Model Info
class ModelInfo(BaseModel):
    """Claude model information"""
    id: str = Field(..., description="Model ID")
    display_name: str = Field(..., description="Human-readable model name")
    created_at: Optional[str] = Field(None, description="Model creation date")
    type: str = Field(..., description="Model type")


class ModelsResponse(BaseModel):
    """Available models response"""
    models: List[ModelInfo] = Field(..., description="List of available models")
    default_model: str = Field(..., description="Default model ID")


# Document Models
class DocumentMetadata(BaseModel):
    """Document metadata"""
    id: str = Field(..., description="Unique document ID")
    filename: str = Field(..., description="Original filename")
    file_type: str = Field(..., description="File extension")
    file_size: int = Field(..., description="File size in bytes")
    uploaded_at: str = Field(..., description="Upload timestamp")
    chunks_count: int = Field(..., description="Number of chunks created")
    word_count: int = Field(0, description="Total word count")
    character_count: int = Field(0, description="Total character count")


class DocumentUploadResponse(BaseModel):
    """Response after document upload"""
    document_id: str = Field(..., description="Generated document ID")
    filename: str = Field(..., description="Uploaded filename")
    chunks_created: int = Field(..., description="Number of chunks created")
    message: str = Field(..., description="Success message")
    stats: Optional[Dict] = Field(None, description="Document statistics")


class DocumentListItem(BaseModel):
    """Document list item"""
    id: str
    filename: str
    uploaded_at: str
    chunks_count: int
    file_size: int
    word_count: int


class DocumentDeleteResponse(BaseModel):
    """Response after document deletion"""
    message: str
    document_id: str
    filename: str
    chunks_deleted: int


# Search Models
class SearchQuery(BaseModel):
    """Search query request"""
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(5, ge=1, le=20, description="Number of results")
    min_similarity: float = Field(0.5, ge=0.0, le=1.0, description="Minimum similarity threshold")


class SearchResult(BaseModel):
    """Single search result"""
    chunk_id: str
    document_id: str
    content: str
    filename: str
    similarity: float
    chunk_index: int


class SearchResponse(BaseModel):
    """Search results response"""
    query: str
    results: List[SearchResult]
    total_results: int
    timestamp: str


# Health Check Models
class HealthStatus(BaseModel):
    """API health status"""
    status: str
    timestamp: str
    environment: Dict[str, str]
    vector_database: Optional[Dict] = None
    redis: Optional[Dict] = None
    message: str


# Error Models
class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    timestamp: str