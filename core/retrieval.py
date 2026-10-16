"""BM25 document retrieval module."""
import json
from pathlib import Path
from typing import List, Tuple
from collections import defaultdict
import math


class BM25:
    """BM25 search implementation for document retrieval."""

    def __init__(self, documents: List[dict], k1: float = 1.5, b: float = 0.75):
        """Initialize BM25 with documents.

        Args:
            documents: List of documents with 'id', 'title', and 'content'
            k1: Saturation parameter (default 1.5)
            b: Length normalization parameter (default 0.75)
        """
        self.documents = documents
        self.k1 = k1
        self.b = b

        # Build inverted index
        self.inverted_index = defaultdict(list)
        self.doc_lengths = {}
        self.term_frequencies = defaultdict(lambda: defaultdict(int))

        for doc_idx, doc in enumerate(documents):
            content = (doc.get('title', '') + ' ' + doc.get('content', '')).lower().split()
            self.doc_lengths[doc_idx] = len(content)

            for term in content:
                self.inverted_index[term].append(doc_idx)
                self.term_frequencies[doc_idx][term] += 1

        self.avg_doc_length = sum(self.doc_lengths.values()) / len(self.documents) if documents else 0
        self.num_docs = len(documents)

    def search(self, query: str, top_k: int = 5) -> List[Tuple[dict, float]]:
        """Search for documents matching query.

        Args:
            query: Search query string
            top_k: Number of top results to return

        Returns:
            List of (document, score) tuples
        """
        terms = query.lower().split()
        scores = defaultdict(float)

        for term in terms:
            if term not in self.inverted_index:
                continue

            idf = math.log((self.num_docs - len(self.inverted_index[term]) + 0.5) /
                          (len(self.inverted_index[term]) + 0.5) + 1)

            for doc_idx in self.inverted_index[term]:
                tf = self.term_frequencies[doc_idx][term]
                doc_len = self.doc_lengths[doc_idx]

                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / self.avg_doc_length))

                scores[doc_idx] += idf * (numerator / denominator)

        # Sort and return top-k
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [(self.documents[doc_idx], score) for doc_idx, score in ranked]


class DataLoader:
    """Load and manage data bundles."""

    @staticmethod
    def load_documents(data_dir: str = "data") -> List[dict]:
        """Load all documents from data directory."""
        docs = []
        data_path = Path(data_dir)

        if not data_path.exists():
            return []

        for json_file in data_path.glob("*.json"):
            with open(json_file) as f:
                data = json.load(f)
                if isinstance(data, list):
                    docs.extend(data)
                else:
                    docs.append(data)

        return docs

    @staticmethod
    def load_tariff_rates(filepath: str = "data/tariff_rates.json") -> dict:
        """Load tariff rates from JSON file."""
        path = Path(filepath)
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return {}

    @staticmethod
    def load_rules(filepath: str = "data/rules.json") -> dict:
        """Load business rules from JSON file."""
        path = Path(filepath)
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return {}
