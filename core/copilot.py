"""Tool A: Query-Reply Copilot - Draft responses with document citations."""
from typing import List, Dict, Tuple
from decimal import Decimal
from dataclasses import dataclass
from .retrieval import BM25, DataLoader
from .llm import LLMClient


@dataclass
class DocumentChunk:
    """A chunk of a document with source information."""
    source: str
    line_number: int
    content: str


class QueryReplyCopilot:
    """Drafts cited replies to customs officer queries."""

    def __init__(self, llm_client: LLMClient = None, enable_llm: bool = False):
        """Initialize the copilot.

        Args:
            llm_client: Optional LLM client for AI-powered responses
            enable_llm: Whether to use LLM (requires API key)
        """
        self.llm_client = llm_client or LLMClient(api_key=None)
        self.enable_llm = enable_llm and self.llm_client.client is not None

        # Load documents and create BM25 index
        self.documents = DataLoader.load_documents()
        self.bm25 = BM25(self.documents)
        self.rules = DataLoader.load_rules()

    def process_query(self, query: str, shipment_id: str, documents: List[Dict] = None) -> Dict:
        """Process a customs officer query about a shipment.

        Args:
            query: The officer's question
            shipment_id: ID of the shipment being queried
            documents: Optional list of shipment documents

        Returns:
            Dictionary with draft response, citations, and verification status
        """
        # Retrieve relevant documents
        relevant_docs = self.bm25.search(query, top_k=5)

        # Verify required documents are present
        required_check = self._check_required_documents(shipment_id, documents or [])

        # Build context with citations
        context = self._build_context(relevant_docs, documents)

        # Draft response using LLM or offline mode
        if self.enable_llm:
            draft_response = self.llm_client.draft_response(query, context)
        else:
            draft_response = self._generate_offline_response(query, context)

        # Verify citations
        citation_check = self.llm_client.verify_citations(draft_response, context)

        return {
            "query": query,
            "draft_response": draft_response,
            "citations": context,
            "verification": {
                "documents_valid": required_check["valid"],
                "missing_documents": required_check["missing"],
                "citations_valid": citation_check["valid"],
            },
            "ready_for_approval": required_check["valid"] and citation_check["valid"]
        }

    def _check_required_documents(self, shipment_id: str, documents: List[Dict]) -> Dict:
        """Check if all required documents are provided.

        Args:
            shipment_id: ID of the shipment
            documents: List of provided documents

        Returns:
            Verification result
        """
        required = self.rules.get("required_documents", [])
        provided_types = {doc.get("type") for doc in documents}

        missing = [doc_type for doc_type in required if doc_type not in provided_types]

        return {
            "valid": len(missing) == 0,
            "missing": missing
        }

    def _build_context(self, relevant_docs: List[Tuple], documents: List[Dict] = None) -> List[Dict]:
        """Build context for LLM with citations.

        Args:
            relevant_docs: Results from BM25 search
            documents: Original shipment documents

        Returns:
            List of context chunks with source information
        """
        context = []

        for doc, score in relevant_docs:
            context.append({
                "source": doc.get("id", "Unknown"),
                "content": doc.get("content", ""),
                "score": float(score)
            })

        if documents:
            for doc in documents:
                context.append({
                    "source": f"Shipment Document: {doc.get('name', 'Unknown')}",
                    "content": doc.get("content", ""),
                    "score": 1.0
                })

        return context

    def _generate_offline_response(self, query: str, context: List[Dict]) -> str:
        """Generate response without LLM (offline/default mode).

        Args:
            query: The officer's query
            context: Context documents

        Returns:
            Draft response
        """
        if not context:
            return f"To answer your query about '{query}', I need access to the shipment documents. Please provide the invoice, packing list, and other relevant documents."

        response = f"Regarding your query about {query}:\n\n"

        for i, chunk in enumerate(context, 1):
            response += f"• From {chunk.get('source', 'document')}: {chunk.get('content', '')}\n"

        response += "\n---\nThis is a draft response. Please review and verify all information before sending. A licensed customs professional should validate the content."

        return response

    def extract_line_citations(self, document_text: str) -> List[DocumentChunk]:
        """Extract and number lines from document for citation.

        Args:
            document_text: Full document text

        Returns:
            List of document chunks with line numbers
        """
        chunks = []
        for line_num, line in enumerate(document_text.split('\n'), 1):
            if line.strip():
                chunks.append(DocumentChunk(
                    source="document",
                    line_number=line_num,
                    content=line.strip()
                ))
        return chunks
