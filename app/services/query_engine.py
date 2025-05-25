from typing import List, Dict, Any, Optional
from langchain.chains import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langchain.schema import Document

from app.services.embedder import EmbeddingService
from config.config import settings


class QueryEngine:
    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )

    def _get_model(self, user_plan: str, has_images: bool = False):
        """Get the appropriate model based on user plan and content"""
        if has_images:
            # Use vision model for images
            return ChatOpenAI(
                model=settings.VISION_MODEL,
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0.7
            )
        elif user_plan == "free":
            # Use free model for free users
            return ChatOpenAI(
                model=settings.FREE_MODEL,
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0.7
            )
        else:
            # Use premium model for paid users
            return ChatOpenAI(
                model=settings.DEFAULT_MODEL,
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0.7
            )

    def _create_prompt_templates(self):
        """Create prompt templates for the chain"""
        # Template for questions that need context
        qa_template = """You are AnyDocAI, an AI document assistant that helps users understand their documents.

        Use the following context from the user's documents to answer their question. If you don't know the answer, say you don't know.
        Don't try to make up an answer. Always be helpful, concise, and professional.

        Context: {context}

        Chat History: {chat_history}

        Question: {question}

        Answer:"""

        qa_prompt = PromptTemplate(
            input_variables=["context", "chat_history", "question"],
            template=qa_template
        )

        # Template for follow-up questions
        condense_template = """Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question.

        Chat History: {chat_history}

        Follow Up Question: {question}

        Standalone Question:"""

        condense_prompt = PromptTemplate(
            input_variables=["chat_history", "question"],
            template=condense_template
        )

        return qa_prompt, condense_prompt

    def query(self, query: str, file_ids: List[str], user_plan: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Query the documents with the given query"""
        # Get relevant chunks
        relevant_chunks = self.embedding_service.search_similar_chunks(query, file_ids)

        # Convert to LangChain documents
        documents = [
            Document(
                page_content=chunk["content"],
                metadata={
                    "file_id": chunk["file_id"],
                    "page_number": chunk["page_number"],
                    "chunk_index": chunk["chunk_index"]
                }
            )
            for chunk in relevant_chunks
        ]

        # Check if any documents have images
        has_images = False  # TODO: Implement image detection

        # Get the appropriate model
        llm = self._get_model(user_plan, has_images)

        # Create prompt templates
        qa_prompt, condense_prompt = self._create_prompt_templates()

        # Create retrieval chain
        chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=documents,  # Use the documents directly as a retriever
            memory=self.memory,
            combine_docs_chain_kwargs={"prompt": qa_prompt},
            question_generator_kwargs={"prompt": condense_prompt}
        )

        # Run the chain
        response = chain.run(query)

        # Return the response
        return {
            "response": response,
            "source_documents": documents,
            "model_used": getattr(llm, 'model', getattr(llm, 'model_name', 'unknown'))
        }
