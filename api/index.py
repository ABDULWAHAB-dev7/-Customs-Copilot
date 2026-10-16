"""Main API server using Starlette ASGI framework."""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from starlette.applications import Starlette
from starlette.responses import JSONResponse, FileResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
import json

from core.copilot import QueryReplyCopilot
from core.charges import ChargeChecker
from core.llm import LLMClient


# Initialize tools
llm_client = LLMClient(api_key=os.getenv("GEMINI_API_KEY"))
query_copilot = QueryReplyCopilot(llm_client=llm_client, enable_llm=bool(os.getenv("GEMINI_API_KEY")))
charge_checker = ChargeChecker()


# API Routes
async def health(request):
    """Health check endpoint."""
    return JSONResponse({
        "status": "healthy",
        "version": "1.0.0",
        "llm_available": query_copilot.enable_llm
    })


async def query_reply(request):
    """Process customs officer query and draft reply.

    Request JSON:
    {
        "query": "What documents are needed for this shipment?",
        "shipment_id": "SHIP-001",
        "documents": [{...}]
    }
    """
    try:
        data = await request.json()

        query = data.get("query", "")
        shipment_id = data.get("shipment_id", "")
        documents = data.get("documents", [])

        if not query:
            return JSONResponse({"error": "query parameter required"}, status_code=400)

        # Process query
        result = query_copilot.process_query(query, shipment_id, documents)

        return JSONResponse(result)

    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def check_charges(request):
    """Check invoice charges against tariff rates.

    Request JSON:
    {
        "id": "INV-001",
        "port": "INMAA4",
        "cfs": "CFS-001",
        "charges": [
            {
                "description": "Port handling charge",
                "tariff_ref": "PH001",
                "amount": 1000.00,
                "gst": 180.00
            }
        ]
    }
    """
    try:
        invoice = await request.json()

        if not invoice.get("charges"):
            return JSONResponse({"error": "charges array required"}, status_code=400)

        # Check charges
        result = charge_checker.check_invoice(invoice)

        return JSONResponse(result)

    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def extract_citations(request):
    """Extract cited lines from a document.

    Request JSON:
    {
        "document_text": "Line 1\nLine 2\n..."
    }
    """
    try:
        data = await request.json()
        document_text = data.get("document_text", "")

        if not document_text:
            return JSONResponse({"error": "document_text required"}, status_code=400)

        chunks = query_copilot.extract_line_citations(document_text)

        result = {
            "total_lines": len(chunks),
            "chunks": [
                {
                    "line_number": c.line_number,
                    "content": c.content
                }
                for c in chunks
            ]
        }

        return JSONResponse(result)

    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


async def status(request):
    """Get system status and available models."""
    return JSONResponse({
        "status": "operational",
        "tools": {
            "query_reply": "Drafts cited responses to customs queries",
            "check_charges": "Validates charges against tariff rates"
        },
        "llm_mode": "enabled" if query_copilot.enable_llm else "offline",
        "model": query_copilot.llm_client.model if query_copilot.enable_llm else "offline"
    })


# Create Starlette app
routes = [
    Route("/api/health", health, methods=["GET"]),
    Route("/api/status", status, methods=["GET"]),
    Route("/api/query-reply", query_reply, methods=["POST"]),
    Route("/api/check-charges", check_charges, methods=["POST"]),
    Route("/api/extract-citations", extract_citations, methods=["POST"]),
]

app = Starlette(routes=routes)

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend
public_dir = Path(__file__).parent.parent / "public"
if public_dir.exists():
    app.mount("/", StaticFiles(directory=str(public_dir), html=True))


# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
