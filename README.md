# Customs Copilot - AI-Powered Customs Assistant

A zero-cost, stateless application that helps with customs clearance using two main tools:
- **Tool A**: Query-Reply Copilot - Draft cited responses to customs officer queries
- **Tool B**: Charge Checker - Validate port/CFS charges against tariff rates

## Quick Start

### Prerequisites
- Python 3.11+
- pip

### Setup

1. **Clone/Extract the project**
```bash
cd custom\ copilot
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set environment variables (optional)**
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY if you have one
```

5. **Run locally**
```bash
python api/index.py
```

The application will be available at `http://localhost:8000`

## Project Structure

```
custom copilot/
├── api/
│   ├── __init__.py
│   └── index.py          # Main ASGI application (Starlette)
├── core/
│   ├── __init__.py
│   ├── copilot.py        # Tool A: Query-reply logic
│   ├── charges.py        # Tool B: Charge validation
│   ├── retrieval.py      # BM25 search & data loading
│   └── llm.py            # LLM integration (Gemini/Claude)
├── data/
│   ├── tariff_rates.json # Tariff rate reference
│   ├── rules.json        # Business rules
│   └── sample_documents.json
├── public/
│   └── index.html        # Frontend UI (static HTML/CSS/JS)
├── requirements.txt
├── vercel.json           # Vercel deployment config
└── README.md
```

## Features

### Tool A: Query-Reply Copilot
- Answer customs officer queries with cited references
- Works in offline mode (default) or with AI enhancement
- Verifies required documents are present
- Ensures all statements are backed by documents

### Tool B: Charge Checker
- Validates charges against tariff rates
- Flags wrong rates, duplicate charges, GST errors
- Deterministic decimal-based calculations
- Shows tariff references for each flagged issue

## API Endpoints

### Query-Reply
```
POST /api/query-reply
{
  "query": "What documents are needed?",
  "shipment_id": "SHIP-001",
  "documents": [{"name": "invoice.pdf", "content": "..."}]
}
```

### Charge Checker
```
POST /api/check-charges
{
  "id": "INV-001",
  "port": "INMAA4",
  "charges": [
    {"description": "Port handling", "tariff_ref": "PH001", "amount": 1000, "gst": 180}
  ]
}
```

### System Status
```
GET /api/status
GET /api/health
```

## Deployment

### Vercel (Zero-Cost)
1. Push to GitHub
2. Connect to Vercel
3. Deploy - automatic!

The app runs on Vercel's free tier with:
- Static frontend hosting
- Python serverless functions
- No database required

### Local Development
```bash
pip install -r requirements.txt
python api/index.py
```

## AI Integration (Optional)

The system works perfectly in **offline mode** without any API keys. To add AI-powered responses:

1. **Get a Gemini API key** from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. **Add to environment**:
   ```bash
   export GEMINI_API_KEY=your_key_here
   ```
3. Restart the app - AI features now enabled

## Configuration

Key settings in `data/rules.json`:
- Required documents for clearance
- Free days policies
- GST rate (default: 18%)
- Currency (INR)

Tariff rates in `data/tariff_rates.json`:
- Port-specific rates
- Rate per charge type

## Testing

### Test Query-Reply
```bash
curl -X POST http://localhost:8000/api/query-reply \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What documents do I need?",
    "shipment_id": "SHIP-001"
  }'
```

### Test Charge Checker
```bash
curl -X POST http://localhost:8000/api/check-charges \
  -H "Content-Type: application/json" \
  -d '{
    "id": "INV-001",
    "port": "INMAA4",
    "charges": [{"description": "Port handling", "tariff_ref": "PH001", "amount": 1000, "gst": 180}]
  }'
```

## Security & Privacy

- **Stateless**: No data stored on server
- **Privacy-First**: All documents processed in memory only
- **No Database**: Uses only read-only JSON data
- **Offline-Ready**: Works without internet connection
- **Citations**: Every statement is sourced from documents

## Roadmap

### V2 Features
- Real PDF document intake
- User authentication & persistence
- Audit logging
- Real ICEGATE integration
- Multi-language support
- Mobile app

## Support

For issues or questions:
1. Check the API endpoints documentation above
2. Review the system design PDF
3. Test in offline mode first
4. Enable debug logging for troubleshooting

## License

MIT License - See LICENSE file for details

---

**Built with**: Python • Starlette • Vercel • Zero Dependencies ❤️
