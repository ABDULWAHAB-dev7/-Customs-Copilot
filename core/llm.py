"""LLM integration module for query-reply drafting."""
import os
from typing import Optional, List, Dict
import json


class LLMClient:
    """Client for interacting with LLM APIs (Gemini, Claude, etc)."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-pro"):
        """Initialize LLM client.

        Args:
            api_key: API key for the LLM service
            model: Model identifier (e.g., 'gemini-pro', 'claude-3-sonnet')
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        self.client = None

        if self.api_key:
            self._initialize_client()

    def _initialize_client(self):
        """Initialize the actual LLM client based on model type."""
        try:
            if "gemini" in self.model.lower():
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.client = genai.GenerativeModel(self.model)
        except ImportError:
            pass

    def draft_response(self, query: str, context: List[Dict]) -> str:
        """Draft a response to a customs officer query using retrieved documents.

        Args:
            query: The officer's query
            context: List of relevant document chunks with citations

        Returns:
            Draft response with citations
        """
        if not self.client:
            return self._offline_response(query, context)

        prompt = self._build_prompt(query, context)

        try:
            response = self.client.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"LLM error: {e}, falling back to offline mode")
            return self._offline_response(query, context)

    def _build_prompt(self, query: str, context: List[Dict]) -> str:
        """Build prompt for the LLM with context and instructions."""
        context_str = "\n".join([
            f"Document: {chunk.get('source', 'Unknown')}\n{chunk.get('content', '')}"
            for chunk in context
        ])

        return f"""You are a customs expert assistant. Draft a response to the following query using ONLY the provided documents.

Every sentence must be cited to a specific document and line. If information is missing, explicitly state what document needs to be provided.

Query: {query}

Context Documents:
{context_str}

Instructions:
1. Base your response only on the provided documents
2. Cite each fact to its source document
3. If evidence is missing, say what needs to be attached
4. Be concise and professional
5. Use a friendly tone suitable for correspondence

Draft Response:"""

    def _offline_response(self, query: str, context: List[Dict]) -> str:
        """Generate response without LLM (offline mode).

        This is the default fallback when no API key is available.
        """
        if not context:
            return "I need to review your documents to answer this query. Please provide the relevant shipping and invoice documents."

        response = "Based on the documents provided:\n\n"
        for i, chunk in enumerate(context, 1):
            response += f"{i}. {chunk.get('content', '')} (from {chunk.get('source', 'document')})\n"

        response += "\nPlease review the above information. For a complete professional response, I recommend consulting with a licensed customs broker."
        return response

    def verify_citations(self, response: str, context: List[Dict]) -> Dict[str, bool]:
        """Verify that all citations in response are valid.

        Args:
            response: Generated response
            context: Original context documents

        Returns:
            Dictionary of verification results
        """
        verification = {
            "valid": True,
            "missing_citations": [],
            "invalid_citations": []
        }

        context_sources = {chunk.get('source', '') for chunk in context}

        # Simple check: look for document references in response
        for line in response.split('\n'):
            if line.strip() and not any(source in line for source in context_sources):
                if len(line) > 10:  # Ignore short lines
                    verification["invalid_citations"].append(line)
                    verification["valid"] = False

        return verification
