"""
LLM Service for Claude API Integration
Handles response generation, prompt engineering, and RAG
"""

import os
from typing import List, Dict, Optional
from anthropic import Anthropic
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class LLMService:
    """Service for generating responses using Claude"""
    
    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        max_tokens: int = 2048,
        temperature: float = 0.7
    ):
        """
        Initialize Claude LLM service
        
        Args:
            api_key: Anthropic API key
            model: Claude model to use
            max_tokens: Maximum tokens in response
            temperature: Response randomness (0-1)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.default_model = model or os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")
        self.model = self.default_model
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")
        
        try:
            self.client = Anthropic(api_key=self.api_key)
            logger.info(f"✅ Claude LLM initialized: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Claude: {e}")
            raise
    
    def generate_response(
        self,
        query: str,
        context: str = None,
        conversation_history: List[Dict] = None,
        system_prompt: str = None,
        sources: List[Dict] = None,
        model: str = None
    ) -> str:
        """
        Generate a response using Claude with RAG
        
        Args:
            query: User's question
            context: Retrieved context from documents/web
            conversation_history: Previous messages
            system_prompt: Custom system prompt
            sources: List of source documents for citation
            model: Override default model for this request
            
        Returns:
            Generated response text
        """
        try:
            # Use specified model or default
            model_to_use = model or self.model
            
            # Build system prompt
            system = system_prompt or self._build_system_prompt(bool(sources))
            
            # Build the full prompt with context
            full_prompt = self._build_prompt(query, context, sources)
            
            # Prepare messages
            messages = []
            
            # Add conversation history (last 10 messages)
            if conversation_history:
                for msg in conversation_history[-10:]:
                    messages.append({
                        "role": msg.get("role", "user"),
                        "content": msg.get("content", "")
                    })
            
            # Add current query
            messages.append({
                "role": "user",
                "content": full_prompt
            })
            
            logger.info(f"Generating response with {len(messages)} messages using model: {model_to_use}")
            
            # Call Claude API
            response = self.client.messages.create(
                model=model_to_use,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system,
                messages=messages
            )
            
            # Extract response text
            response_text = response.content[0].text
            
            logger.info(f"Generated response: {len(response_text)} characters")
            return response_text
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            raise
    
    def _build_system_prompt(self, has_sources: bool = False) -> str:
        """
        Build the system prompt for Claude
        
        Args:
            has_sources: Whether sources are provided for citation
            
        Returns:
            System prompt string
        """
        base_prompt = """You are a helpful AI assistant with access to a knowledge base and web search capabilities. Your role is to provide accurate, helpful, and well-informed responses.

Guidelines:
- Be concise but thorough in your explanations
- Use the provided context to answer questions accurately
- If the context doesn't contain relevant information, say so clearly
- Be conversational and friendly in tone
- Break down complex topics into understandable parts"""

        if has_sources:
            citation_prompt = """

CRITICAL - Citation Requirements:
- When using information from provided sources, you MUST cite them using [Source N] format
- Place citations immediately after the relevant sentence or claim
- Use multiple citations if information comes from multiple sources: [Source 1][Source 2]
- Be specific about which source supports which claim
- For web sources, acknowledge them as external information
- Example: "Machine learning is a subset of AI [Source 1]. It enables systems to learn from data [Source 2]."

Your response should naturally incorporate citations where appropriate, similar to how Perplexity AI handles references."""
            
            return base_prompt + citation_prompt
        
        return base_prompt
    
    def _build_prompt(
        self,
        query: str,
        context: str = None,
        sources: List[Dict] = None
    ) -> str:
        """
        Build the complete prompt with context and sources
        
        Args:
            query: User query
            context: Retrieved context
            sources: List of sources for citation
            
        Returns:
            Complete prompt string
        """
        prompt_parts = []
        
        # Add context if available
        if context and context.strip():
            prompt_parts.append("# Retrieved Context\n")
            
            # If we have sources, format them with source numbers
            if sources:
                prompt_parts.append("Here is relevant information from various sources:\n")
                
                # Split context by source and number them
                for idx, source in enumerate(sources, 1):
                    source_type = source.get("type", "document")
                    
                    if source_type == "document":
                        filename = source.get("filename", "Unknown")
                        content = source.get("content", "")
                        prompt_parts.append(f"\n[Source {idx}] From document '{filename}':\n{content}\n")
                    
                    elif source_type == "web":
                        title = source.get("title", "Web Result")
                        url = source.get("url", "")
                        content = source.get("content", "")
                        prompt_parts.append(f"\n[Source {idx}] From web - '{title}' ({url}):\n{content}\n")
            else:
                # No sources, just add raw context
                prompt_parts.append(context)
            
            prompt_parts.append("\n---\n")
        
        # Add the user's question
        prompt_parts.append(f"\n# User Question\n{query}\n")
        
        # Add instructions
        if sources:
            prompt_parts.append("\n# Instructions\n")
            prompt_parts.append("Please answer the question using the provided sources. ")
            prompt_parts.append("Remember to cite your sources using [Source N] format after each claim. ")
            prompt_parts.append("Be specific and accurate in your citations.")
        else:
            if context:
                prompt_parts.append("\nPlease answer based on the provided context.")
            else:
                prompt_parts.append("\nPlease provide a helpful answer based on your knowledge.")
        
        return "".join(prompt_parts)
    
    def generate_with_search_results(
        self,
        query: str,
        document_results: List[Dict],
        web_results: List[Dict],
        conversation_history: List[Dict] = None,
        model: str = None
    ) -> tuple[str, List[Dict]]:
        """
        Generate response with both document and web search results
        Returns response and formatted sources
        
        Args:
            query: User query
            document_results: Results from vector database
            web_results: Results from web search
            conversation_history: Previous messages
            model: Override model for this request
            
        Returns:
            Tuple of (response_text, sources_list)
        """
        try:
            # Prepare sources list
            sources = []
            context_parts = []
            
            # Add document sources
            for idx, result in enumerate(document_results):
                source = {
                    "type": "document",
                    "filename": result.get("metadata", {}).get("filename", "Unknown"),
                    "content": result.get("content", ""),
                    "similarity": result.get("similarity", 0),
                    "source_number": len(sources) + 1
                }
                sources.append(source)
                context_parts.append(source["content"])
            
            # Add web sources
            for idx, result in enumerate(web_results):
                source = {
                    "type": "web",
                    "title": result.get("title", "Web Result"),
                    "url": result.get("url", ""),
                    "content": result.get("content", ""),
                    "source_number": len(sources) + 1
                }
                sources.append(source)
                context_parts.append(source["content"])
            
            # Build context
            context = "\n\n".join(context_parts) if context_parts else None
            
            # Generate response with optional model override
            response = self.generate_response(
                query=query,
                context=context,
                conversation_history=conversation_history,
                sources=sources,
                model=model
            )
            
            # Format sources for frontend
            formatted_sources = []
            for source in sources:
                if source["type"] == "document":
                    formatted_sources.append({
                        "type": "document",
                        "source_number": source["source_number"],
                        "filename": source["filename"],
                        "similarity": source.get("similarity", 0),
                        "preview": source["content"][:200] + "..."
                    })
                else:  # web
                    formatted_sources.append({
                        "type": "web",
                        "source_number": source["source_number"],
                        "title": source["title"],
                        "url": source["url"],
                        "preview": source["content"][:200] + "..."
                    })
            
            return response, formatted_sources
            
        except Exception as e:
            logger.error(f"Failed to generate response with search results: {e}")
            raise
    
    def summarize_text(self, text: str, max_length: int = 200) -> str:
        """
        Generate a summary of text
        
        Args:
            text: Text to summarize
            max_length: Maximum length of summary
            
        Returns:
            Summary text
        """
        try:
            prompt = f"Please provide a concise summary (max {max_length} words) of the following text:\n\n{text}"
            
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.3,
                system="You are a helpful assistant that creates concise summaries.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Failed to summarize text: {e}")
            return text[:max_length] + "..."

    def get_available_models(self) -> List[Dict]:
        """
        Get list of available Claude models from API
        
        Returns:
            List of model dictionaries
        """
        try:
            # Call Anthropic models API
            response = self.client.models.list()
            
            models = []
            for model in response.data:
                # Convert datetime to string if needed
                created_at = model.created_at
                if hasattr(created_at, 'isoformat'):
                    created_at = created_at.isoformat()
                
                models.append({
                    "id": model.id,
                    "display_name": model.display_name,
                    "created_at": created_at,
                    "type": model.type
                })
            
            logger.info(f"Retrieved {len(models)} available models")
            return models
            
        except Exception as e:
            logger.error(f"Failed to get models from API: {e}")
            # Return default models as fallback
            return [
                {
                    "id": "claude-sonnet-4-20250514",
                    "display_name": "Claude Sonnet 4",
                    "created_at": "2025-02-19T00:00:00Z",
                    "type": "model"
                },
                {
                    "id": "claude-3-5-sonnet-20240620",
                    "display_name": "Claude 3.5 Sonnet",
                    "created_at": "2024-06-20T00:00:00Z",
                    "type": "model"
                },
                {
                    "id": "claude-3-opus-20240229",
                    "display_name": "Claude 3 Opus",
                    "created_at": "2024-02-29T00:00:00Z",
                    "type": "model"
                },
                {
                    "id": "claude-3-sonnet-20240229",
                    "display_name": "Claude 3 Sonnet",
                    "created_at": "2024-02-29T00:00:00Z",
                    "type": "model"
                },
                {
                    "id": "claude-3-haiku-20240307",
                    "display_name": "Claude 3 Haiku",
                    "created_at": "2024-03-07T00:00:00Z",
                    "type": "model"
                }
            ]


class PromptTemplates:
    """Collection of prompt templates for different use cases"""
    
    @staticmethod
    def conversational_rag(query: str, context: str, history: str) -> str:
        """Prompt for conversational RAG"""
        return f"""Based on the following context and conversation history, please answer the user's question naturally.

Previous Conversation:
{history}

Relevant Context:
{context}

Current Question: {query}

Please provide a conversational response that:
1. Takes into account the conversation history
2. Uses the provided context when relevant
3. Maintains a natural, helpful tone"""
    
    @staticmethod
    def fact_checking(claim: str, context: str) -> str:
        """Prompt for fact checking against context"""
        return f"""Please evaluate the following claim against the provided context:

Claim: {claim}

Context:
{context}

Analysis:
1. Is the claim supported by the context?
2. What evidence supports or contradicts it?
3. Overall assessment: [Supported/Contradicted/Insufficient Information]"""
    
    @staticmethod
    def multi_document_synthesis(query: str, contexts: List[str]) -> str:
        """Prompt for synthesizing information from multiple documents"""
        context_str = "\n\n".join([f"Document {i+1}:\n{ctx}" for i, ctx in enumerate(contexts)])
        
        return f"""You have access to multiple sources. Please synthesize the information to answer comprehensively.

Sources:
{context_str}

Question: {query}

Please provide a comprehensive answer that:
1. Synthesizes information from all sources
2. Notes any agreements or disagreements between sources
3. Provides a balanced perspective"""


# Utility function
def get_llm_service() -> LLMService:
    """Factory function to get LLMService instance"""
    return LLMService()