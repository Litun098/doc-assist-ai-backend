"""
Service for generating suggested queries based on document content.
"""
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import uuid

from fastapi import HTTPException
from llama_index.core import Settings
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.llms.openai import OpenAI

from config.config import settings

logger = logging.getLogger(__name__)

class SuggestionService:
    """Service for generating suggested queries based on document content."""

    def __init__(self, document_service=None, llama_index_service=None, supabase=None):
        """Initialize the suggestion service."""
        from app.services.document_service import document_service as doc_service
        from app.services.llama_index_service import llama_index_service as llama_service

        self.document_service = document_service or doc_service
        self.llama_index_service = llama_index_service or llama_service
        self.supabase = supabase

    async def generate_suggestions(
        self,
        session_id: str,
        user_id: str,
        document_ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Generate suggested queries based on document content.

        Args:
            session_id: ID of the chat session
            user_id: ID of the user
            document_ids: Optional list of document IDs (if not provided, will fetch from session)

        Returns:
            List of suggested queries
        """
        try:
            # If document_ids not provided, fetch from session
            if not document_ids and self.supabase:
                doc_response = self.supabase.table("session_documents").select("document_id").eq("session_id", session_id).execute()
                document_ids = [doc["document_id"] for doc in doc_response.data]

            if not document_ids:
                return self._get_default_suggestions()

            # Get document metadata
            document_metadata = []
            for doc_id in document_ids:
                try:
                    if self.supabase:
                        doc_result = self.supabase.table("documents").select("*").eq("id", doc_id).execute()
                        if doc_result.data:
                            document_metadata.append(doc_result.data[0])
                except Exception as e:
                    logger.error(f"Error fetching document metadata: {str(e)}")

            # Get document content samples
            content_samples = await self._get_document_samples(document_ids, user_id)

            # Generate suggestions based on content
            suggestions = await self._generate_ai_suggestions(content_samples, document_metadata)

            return suggestions

        except Exception as e:
            logger.error(f"Error generating suggestions: {str(e)}")
            return self._get_default_suggestions()

    async def _get_document_samples(self, document_ids: List[str], user_id: str) -> List[str]:
        """
        Get representative samples from documents.

        Args:
            document_ids: List of document IDs
            user_id: ID of the user

        Returns:
            List of document content samples
        """
        samples = []

        try:
            # Use LlamaIndex to get document samples
            for doc_id in document_ids:
                try:
                    # Get a few chunks from each document
                    result = await self.llama_index_service.get_document_chunks(
                        file_id=doc_id,
                        user_id=user_id,
                        limit=3  # Get 3 chunks per document
                    )

                    if result and "chunks" in result and result["chunks"]:
                        # Extract text from chunks
                        for chunk in result["chunks"]:
                            if "content" in chunk and chunk["content"].strip():
                                samples.append(chunk["content"])
                    else:
                        # If no chunks found, try to get document content directly from Supabase
                        if self.supabase:
                            logger.info(f"No chunks found for document {doc_id}, trying to get content from Supabase")
                            doc_result = self.supabase.table("documents").select("*").eq("id", doc_id).execute()
                            if doc_result.data:
                                doc = doc_result.data[0]
                                # If there's a file_path or content field, use it
                                if "file_path" in doc and doc["file_path"]:
                                    try:
                                        with open(doc["file_path"], "r", encoding="utf-8", errors="ignore") as f:
                                            content = f.read(2000)  # Read first 2000 chars
                                            samples.append(content)
                                    except Exception as read_error:
                                        logger.error(f"Error reading file: {str(read_error)}")
                                elif "content" in doc and doc["content"]:
                                    samples.append(doc["content"][:2000])  # First 2000 chars
                except Exception as chunk_error:
                    logger.error(f"Error getting chunks for document {doc_id}: {str(chunk_error)}")

            # If still no samples, try to get document metadata at least
            if not samples and document_ids and self.supabase:
                logger.info("No content samples found, using document metadata")
                for doc_id in document_ids:
                    doc_result = self.supabase.table("documents").select("*").eq("id", doc_id).execute()
                    if doc_result.data:
                        doc = doc_result.data[0]
                        metadata = f"Document: {doc.get('file_name', 'Unknown')}\n"
                        metadata += f"Type: {doc.get('file_type', 'Unknown')}\n"
                        metadata += f"Size: {doc.get('file_size', 'Unknown')}\n"
                        metadata += f"Created: {doc.get('created_at', 'Unknown')}\n"
                        samples.append(metadata)
        except Exception as e:
            logger.error(f"Error getting document samples: {str(e)}")

        # Ensure we have at least some content
        if not samples:
            logger.warning("No document samples found, using placeholder text")
            samples.append("This appears to be a document that needs analysis.")

        return samples[:5]  # Limit to 5 samples total to avoid token limits

    async def _generate_ai_suggestions(
        self,
        content_samples: List[str],
        document_metadata: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Generate suggestions using AI based on document content.

        Args:
            content_samples: List of document content samples
            document_metadata: List of document metadata

        Returns:
            List of suggested queries
        """
        try:
            # Prepare document type information
            doc_types = [doc.get("file_type", "unknown") for doc in document_metadata]
            doc_names = [doc.get("file_name", f"Document {i+1}") for i, doc in enumerate(document_metadata)]

            # If no document metadata available, try to extract info from content samples
            if not doc_types or not doc_names:
                logger.info("No document metadata available, extracting from content")
                doc_types = ["document"]
                doc_names = ["Document"]

                # Try to guess document type from content
                for sample in content_samples:
                    if "spreadsheet" in sample.lower() or "excel" in sample.lower() or "table" in sample.lower():
                        doc_types = ["spreadsheet"]
                        break
                    elif "presentation" in sample.lower() or "slide" in sample.lower() or "powerpoint" in sample.lower():
                        doc_types = ["presentation"]
                        break
                    elif "pdf" in sample.lower():
                        doc_types = ["pdf"]
                        break

            # Combine samples into context
            context = "\n\n---\n\n".join(content_samples)

            # Truncate if too long
            if len(context) > 4000:
                context = context[:4000] + "..."

            # Create prompt for generating suggestions
            messages = [
                ChatMessage(
                    role=MessageRole.SYSTEM,
                    content="""You are an AI assistant that generates helpful suggested questions about documents.
                    Based on the document content and types provided, generate 5 specific, relevant questions that a user might want to ask.
                    Focus on questions that would be useful for understanding the content, extracting insights, or analyzing the information.
                    Make the questions diverse and specific to the actual content.
                    The questions should be directly related to the specific content provided, not generic questions.
                    For example, if the document is about sales data, ask about specific trends, regions, or products mentioned.
                    If it's a text document, ask about specific concepts, arguments, or information mentioned in the text."""
                ),
                ChatMessage(
                    role=MessageRole.USER,
                    content=f"""Here are samples from the user's documents:

Document Types: {', '.join(doc_types)}
Document Names: {', '.join(doc_names)}

Content Samples:
{context}

Generate 5 specific, relevant questions that would be helpful for understanding these documents.
The questions should be directly related to the specific content in the samples, not generic questions.
Return ONLY the questions as a numbered list, with no additional text or explanations."""
                )
            ]

            # Generate suggestions with higher temperature for more diverse questions
            llm = OpenAI(
                model=settings.DEFAULT_MODEL,
                api_key=settings.OPENAI_API_KEY,
                temperature=0.7  # Higher temperature for more creative questions
            )
            response = llm.chat(messages)

            # Parse response into list of questions
            suggestions = []
            for line in response.content.strip().split("\n"):
                # Remove numbering and leading/trailing whitespace
                clean_line = line.strip()
                if clean_line:
                    # Remove numbering (1., 2., etc.)
                    if clean_line[0].isdigit() and len(clean_line) > 1 and clean_line[1:].startswith('. '):
                        clean_line = clean_line[clean_line.index('.')+1:].strip()
                    # Remove other potential numbering formats
                    elif clean_line.startswith('- '):
                        clean_line = clean_line[2:].strip()

                    if clean_line and clean_line not in suggestions:
                        suggestions.append(clean_line)

            # Ensure we have at least some suggestions
            if not suggestions:
                logger.warning("AI didn't generate any valid suggestions, using defaults")
                return self._get_default_suggestions()

            # Log the generated suggestions for debugging
            logger.info(f"Generated {len(suggestions)} suggestions: {suggestions}")

            return suggestions[:5]  # Return at most 5 suggestions

        except Exception as e:
            logger.error(f"Error generating AI suggestions: {str(e)}")
            return self._get_default_suggestions()

    def _get_default_suggestions(self) -> List[str]:
        """
        Get default suggestions when AI generation fails.

        Returns:
            List of default suggested queries
        """
        return [
            "Can you summarize this document?",
            "What are the key points in this document?",
            "Extract the main ideas from this document",
            "What insights can you find in this content?",
            "How would you explain this document in simple terms?"
        ]


# Create a singleton instance
suggestion_service = SuggestionService()
