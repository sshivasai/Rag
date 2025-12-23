"""
Document Processing Service
Handles text extraction, chunking, and document management
"""

import os
import re
from typing import List, Dict, Optional
from datetime import datetime
import logging
from pypdf import PdfReader
import json

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Service for processing and chunking documents"""
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        strategy: str = None
    ):
        """
        Initialize document processor
        
        Args:
            chunk_size: Size of each chunk (in characters for char-based, tokens for token-based)
            chunk_overlap: Number of overlapping characters/tokens between chunks
            strategy: Chunking strategy ('tokens', 'sentences', 'paragraphs', 'fixed')
        """
        self.chunk_size = chunk_size or int(os.getenv("CHUNK_SIZE", "512"))
        self.chunk_overlap = chunk_overlap or int(os.getenv("CHUNK_OVERLAP", "50"))
        self.strategy = strategy or os.getenv("CHUNKING_STRATEGY", "tokens")
        
        logger.info(f"DocumentProcessor initialized: strategy={self.strategy}, "
                   f"chunk_size={self.chunk_size}, overlap={self.chunk_overlap}")
    
    def extract_text_from_file(self, file_path: str, filename: str) -> str:
        """
        Extract text from various file formats
        
        Args:
            file_path: Path to the file
            filename: Original filename with extension
            
        Returns:
            Extracted text content
        """
        file_ext = os.path.splitext(filename)[1].lower()
        
        logger.info(f"Extracting text from {filename} (type: {file_ext})")
        
        try:
            if file_ext == '.txt':
                return self._extract_from_txt(file_path)
            elif file_ext == '.pdf':
                return self._extract_from_pdf(file_path)
            elif file_ext == '.json':
                return self._extract_from_json(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")
                
        except Exception as e:
            logger.error(f"Failed to extract text from {filename}: {e}")
            raise
    
    def _extract_from_txt(self, file_path: str) -> str:
        """Extract text from .txt file"""
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, errors='strict') as f:
                    text = f.read()
                    # Check if text looks valid (no null bytes)
                    if '\x00' not in text:
                        logger.info(f"Extracted {len(text)} characters from txt file (encoding: {encoding})")
                        return text
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        # Fallback: read as binary and decode with errors='ignore'
        with open(file_path, 'rb') as f:
            content = f.read()
            # Try to detect encoding
            if content.startswith(b'\xff\xfe') or content.startswith(b'\xfe\xff'):
                # UTF-16 with BOM
                text = content.decode('utf-16', errors='ignore')
            else:
                text = content.decode('utf-8', errors='ignore')
        
        # Remove null bytes if any remain
        text = text.replace('\x00', '')
        
        logger.info(f"Extracted {len(text)} characters from txt file (fallback)")
        return text
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from .pdf file"""
        try:
            reader = PdfReader(file_path)
            text_parts = []
            
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            text = "\n\n".join(text_parts)
            logger.info(f"Extracted {len(text)} characters from {len(reader.pages)} PDF pages")
            return text
            
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            raise ValueError(f"Failed to extract text from PDF: {e}")
    
    def _extract_from_json(self, file_path: str) -> str:
        """Extract text from .json file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert JSON to readable text
        text = json.dumps(data, indent=2)
        logger.info(f"Extracted {len(text)} characters from JSON file")
        return text
    
    def chunk_text(self, text: str, strategy: str = None) -> List[str]:
        """
        Chunk text using specified strategy
        
        Args:
            text: Text to chunk
            strategy: Chunking strategy (overrides default)
            
        Returns:
            List of text chunks
        """
        strategy = strategy or self.strategy
        
        logger.info(f"Chunking text ({len(text)} chars) using strategy: {strategy}")
        
        if strategy == "sentences":
            chunks = self._chunk_by_sentences(text)
        elif strategy == "paragraphs":
            chunks = self._chunk_by_paragraphs(text)
        elif strategy == "fixed":
            chunks = self._chunk_by_fixed_size(text)
        else:  # default to tokens
            chunks = self._chunk_by_tokens(text)
        
        logger.info(f"Created {len(chunks)} chunks")
        return chunks
    
    def _chunk_by_tokens(self, text: str) -> List[str]:
        """
        Chunk text by approximate token count
        Uses word-based approximation: 1 token ≈ 0.75 words
        """
        # Split into words
        words = text.split()
        
        # Convert token size to word count
        word_chunk_size = int(self.chunk_size * 0.75)
        word_overlap = int(self.chunk_overlap * 0.75)
        
        chunks = []
        start = 0
        
        while start < len(words):
            end = start + word_chunk_size
            chunk_words = words[start:end]
            chunk = ' '.join(chunk_words)
            
            if chunk.strip():
                chunks.append(chunk.strip())
            
            start = end - word_overlap
        
        return chunks
    
    def _chunk_by_sentences(self, text: str) -> List[str]:
        """Chunk text by sentences"""
        # Simple sentence splitter
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Group sentences into chunks
        chunk_size_sentences = max(1, self.chunk_size // 100)  # Approximate sentences per chunk
        overlap_sentences = max(0, self.chunk_overlap // 100)
        
        chunks = []
        start = 0
        
        while start < len(sentences):
            end = start + chunk_size_sentences
            chunk_sentences = sentences[start:end]
            chunk = '. '.join(chunk_sentences) + '.'
            
            if chunk.strip():
                chunks.append(chunk.strip())
            
            start = end - overlap_sentences
        
        return chunks
    
    def _chunk_by_paragraphs(self, text: str) -> List[str]:
        """Chunk text by paragraphs"""
        paragraphs = text.split('\n\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            if current_size + para_size > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append('\n\n'.join(current_chunk))
                
                # Start new chunk with overlap
                if self.chunk_overlap > 0 and current_chunk:
                    current_chunk = [current_chunk[-1], para]
                    current_size = len(current_chunk[-1]) + para_size
                else:
                    current_chunk = [para]
                    current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size
        
        # Add remaining chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks
    
    def _chunk_by_fixed_size(self, text: str) -> List[str]:
        """Chunk text by fixed character size"""
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = start + self.chunk_size
            chunk = text[start:end]
            
            if chunk.strip():
                chunks.append(chunk.strip())
            
            start = end - self.chunk_overlap
        
        return chunks
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove very long repeated characters
        text = re.sub(r'(.)\1{5,}', r'\1\1', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def get_text_stats(self, text: str) -> Dict:
        """
        Get statistics about the text
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with text statistics
        """
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        paragraphs = text.split('\n\n')
        
        return {
            "characters": len(text),
            "words": len(words),
            "sentences": len([s for s in sentences if s.strip()]),
            "paragraphs": len([p for p in paragraphs if p.strip()]),
            "avg_word_length": sum(len(w) for w in words) / len(words) if words else 0
        }
    
    def validate_file(self, filename: str, max_size_mb: int = 10) -> tuple[bool, str]:
        """
        Validate file before processing
        
        Args:
            filename: Name of the file
            max_size_mb: Maximum allowed file size in MB
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file extension
        allowed_extensions = ['.txt', '.pdf', '.json']
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            return False, f"File type {file_ext} not supported. Allowed: {allowed_extensions}"
        
        return True, ""
    
    def process_document(
        self,
        file_path: str,
        filename: str,
        clean: bool = True
    ) -> tuple[str, List[str], Dict]:
        """
        Complete document processing pipeline
        
        Args:
            file_path: Path to the file
            filename: Original filename
            clean: Whether to clean the text
            
        Returns:
            Tuple of (full_text, chunks, stats)
        """
        logger.info(f"Processing document: {filename}")
        
        # Extract text
        text = self.extract_text_from_file(file_path, filename)
        
        # Clean text if requested
        if clean:
            text = self.clean_text(text)
        
        # Get statistics
        stats = self.get_text_stats(text)
        
        # Chunk text
        chunks = self.chunk_text(text)
        
        logger.info(f"Document processed: {stats['words']} words, {len(chunks)} chunks")
        
        return text, chunks, stats


# Utility functions
def get_document_processor() -> DocumentProcessor:
    """Factory function to get DocumentProcessor instance"""
    return DocumentProcessor()


def supported_file_types() -> List[str]:
    """Get list of supported file types"""
    return ['.txt', '.pdf', '.json']