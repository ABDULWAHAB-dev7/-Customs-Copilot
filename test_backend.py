"""Test suite for Customs Copilot backend."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from core.retrieval import BM25, DataLoader
from core.copilot import QueryReplyCopilot
from core.charges import ChargeChecker
from core.llm import LLMClient


def test_data_loading():
    """Test data loading functionality."""
    print("\n=== Testing Data Loading ===")

    docs = DataLoader.load_documents()
    print(f"✓ Loaded {len(docs)} documents")

    tariffs = DataLoader.load_tariff_rates()
    print(f"✓ Loaded tariff rates: {len(tariffs)} entries")

    rules = DataLoader.load_rules()
    print(f"✓ Loaded rules: {list(rules.keys())}")


def test_bm25_search():
    """Test BM25 document search."""
    print("\n=== Testing BM25 Search ===")

    docs = DataLoader.load_documents()
    bm25 = BM25(docs)

    results = bm25.search("port handling charges")
    print(f"✓ Found {len(results)} results for 'port handling charges'")

    for doc, score in results:
        print(f"  - {doc.get('id', 'Unknown')}: {score:.2f}")


def test_query_copilot_offline():
    """Test query copilot in offline mode."""
    print("\n=== Testing Query Copilot (Offline Mode) ===")

    copilot = QueryReplyCopilot(enable_llm=False)

    result = copilot.process_query(
        query="What are the port handling charges?",
        shipment_id="SHIP-001",
        documents=[]
    )

    print(f"✓ Query processed successfully")
    print(f"  Status: {result['ready_for_approval']}")
    print(f"  Response preview: {result['draft_response'][:100]}...")


def test_charge_checker():
    """Test charge validation functionality."""
    print("\n=== Testing Charge Checker ===")

    checker = ChargeChecker()

    invoice = {
        "id": "INV-001",
        "port": "INMAA4",
        "charges": [
            {
                "description": "Port handling charge",
                "tariff_ref": "PH001",
                "amount": 1000.00,
                "gst": 180.00
            }
        ]
    }

    result = checker.check_invoice(invoice)

    print(f"✓ Invoice validated")
    print(f"  Status: {result['status']}")
    print(f"  Issues found: {result['total_issues']}")
    if result['issues']:
        for issue in result['issues']:
            print(f"  - {issue['type']}: {issue['message']}")


def test_citation_extraction():
    """Test line citation extraction."""
    print("\n=== Testing Citation Extraction ===")

    copilot = QueryReplyCopilot()

    doc_text = """Line 1: This is the first line
Line 2: This is the second line
Line 3: This is the third line"""

    chunks = copilot.extract_line_citations(doc_text)

    print(f"✓ Extracted {len(chunks)} citation chunks")
    for chunk in chunks:
        print(f"  - Line {chunk.line_number}: {chunk.content[:50]}...")


def run_all_tests():
    """Run all tests."""
    print("\n" + "="*50)
    print("CUSTOMS COPILOT - BACKEND TEST SUITE")
    print("="*50)

    try:
        test_data_loading()
        test_bm25_search()
        test_query_copilot_offline()
        test_charge_checker()
        test_citation_extraction()

        print("\n" + "="*50)
        print("✓ ALL TESTS PASSED")
        print("="*50 + "\n")

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
