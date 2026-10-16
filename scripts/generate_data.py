"""Writes the synthetic data bundle in data/. Deterministic: no randomness."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

INVOICE = [
    "Invoice No: INV-1001",
    "Supplier: Sample Exporter Ltd",
    "Buyer: Sample Importer Pvt Ltd",
    "Invoice Date: 2026-09-20",
    "Currency: USD",
    "Invoice Value: 12500.00",
    "Incoterm: FOB",
    "HS Code: 8524.11",
    "Goods Description: Test sockets for semiconductor devices",
]
PACKING = [
    "Packing List No: PL-1001",
    "Container No: SMPU0000101",
    "Total Packages: 40",
    "Gross Weight: 812.50 kg",
    "Net Weight: 790.00 kg",
]
BOL = [
    "B/L No: BL-1001",
    "Vessel: MV Sample Star",
    "Voyage: 2609W",
    "Port of Loading: Sample Port Origin",
    "Port of Discharge: Sample Port India",
    "Packages: 40",
    "Gross Weight: 812.50 kg",
]
CERT = [
    "Certificate No: CO-1001",
    "Country of Origin: Sample Country",
    "HS Code: 8524.11",
    "Exemption Notification: 12/2026-Sample",
    "Issued By: Sample Chamber",
]

SHIPMENTS = [
    {"id": "SHP-1001", "docs": {"invoice": INVOICE, "packing_list": PACKING,
                                "bill_of_lading": BOL, "certificate_of_origin": CERT}},
    {"id": "SHP-1002", "docs": {"invoice": INVOICE,
                                "packing_list": PACKING,
                                "certificate_of_origin": [l if not l.startswith("HS Code") else "HS Code: 8524.19" for l in CERT]}},
    {"id": "SHP-1003", "docs": {"invoice": INVOICE, "packing_list": PACKING,
                                "bill_of_lading": [l if not l.startswith("Packages") else "Packages: 38" for l in BOL],
                                "certificate_of_origin": CERT}},
]

QUESTIONS = [
    "Provide the CTH declared for this shipment.",
    "What is the declared invoice value and currency?",
    "What is the country of origin of the goods?",
    "Are you claiming any customs exemption notification?",
    "What is the total quantity and gross weight?",
    "Which vessel and voyage carry this consignment?",
    "Please confirm the goods description.",
]

TARIFFS = {
    "SAMPLE_A": {
        "terminal": "Sample CFS Terminal A",
        "gst_percent": "18",
        "charges": {
            "HANDLING": {"description": "Container handling", "unit": "box", "rate": {"20": "1500.00", "40": "2400.00"}},
            "DOC": {"description": "Documentation", "unit": "bill", "rate": {"20": "300.00", "40": "300.00"}},
            "SEAL": {"description": "Seal charge", "unit": "seal", "rate": {"20": "150.00", "40": "150.00"}},
        },
        "storage": {
            "free_days": 3,
            "slabs": {
                "20": [[1, 3, "300.00"], [4, 7, "450.00"], [8, None, "600.00"]],
                "40": [[1, 3, "450.00"], [4, 7, "600.00"], [8, None, "800.00"]],
            },
        },
    },
    "SAMPLE_B": {
        "terminal": "Sample CFS Terminal B",
        "gst_percent": "18",
        "charges": {
            "HANDLING": {"description": "Container handling", "unit": "box", "rate": {"20": "1200.00", "40": "2000.00"}},
            "DOC": {"description": "Documentation", "unit": "bill", "rate": {"20": "250.00", "40": "250.00"}},
        },
        "storage": {
            "free_days": 2,
            "slabs": {"20": [[1, 2, "350.00"], [3, None, "500.00"]], "40": [[1, 2, "500.00"], [3, None, "700.00"]]},
        },
    },
}


def invoice_text(terminal, no, size, gate_in, gate_out, lines, subtotal, gst, total):
    head = [
        f"TERMINAL: {terminal}",
        f"INVOICE NO: {no}",
        "CONTAINER: SMPU0000101",
        f"SIZE: {size}",
        f"GATE IN: {gate_in}",
        f"GATE OUT: {gate_out}",
    ]
    body = [f"LINE {i} | {c} | {d} | {q} | {r} | {a}" for i, (c, d, q, r, a) in enumerate(lines, 1)]
    foot = [f"SUBTOTAL: {subtotal}", f"GST: {gst}", f"TOTAL: {total}"]
    return "\n".join(head + body + foot)


CFS = [
    {
        "id": "CFS-A-101", "terminal": "Sample CFS Terminal A", "tariff_id": "SAMPLE_A",
        "text": invoice_text("Sample CFS Terminal A", "CFS-A-101", 20, "2026-10-01", "2026-10-06", [
            ("HANDLING", "Container handling", 1, "1500.00", "1500.00"),
            ("DOC", "Documentation", 1, "300.00", "300.00"),
            ("STORAGE", "Storage days", 2, "300.00", "600.00"),
        ], "2400.00", "432.00", "2832.00"),
        "gold": {"flags": []},
    },
    {
        "id": "CFS-A-102", "terminal": "Sample CFS Terminal A", "tariff_id": "SAMPLE_A",
        "text": invoice_text("Sample CFS Terminal A", "CFS-A-102", 20, "2026-10-01", "2026-10-06", [
            ("HANDLING", "Container handling", 1, "1500.00", "1500.00"),
            ("DOC", "Documentation", 1, "300.00", "300.00"),
            ("STORAGE", "Storage days", 4, "300.00", "1200.00"),
        ], "3000.00", "540.00", "3540.00"),
        "gold": {"flags": ["STORAGE_DAYS"]},
    },
    {
        "id": "CFS-A-103", "terminal": "Sample CFS Terminal A", "tariff_id": "SAMPLE_A",
        "text": invoice_text("Sample CFS Terminal A", "CFS-A-103", 20, "2026-10-01", "2026-10-06", [
            ("HANDLING", "Container handling", 1, "1800.00", "1800.00"),
            ("DOC", "Documentation", 1, "300.00", "300.00"),
            ("DOC", "Documentation", 1, "300.00", "300.00"),
            ("STORAGE", "Storage days", 2, "300.00", "600.00"),
        ], "3000.00", "540.00", "3540.00"),
        "gold": {"flags": ["RATE_MISMATCH", "DUPLICATE"]},
    },
    {
        "id": "CFS-A-104", "terminal": "Sample CFS Terminal A", "tariff_id": "SAMPLE_A",
        "text": invoice_text("Sample CFS Terminal A", "CFS-A-104", 20, "2026-10-01", "2026-10-06", [
            ("HANDLING", "Container handling", 1, "1500.00", "1500.00"),
            ("DOC", "Documentation", 1, "300.00", "300.00"),
            ("STORAGE", "Storage days", 2, "300.00", "600.00"),
        ], "2400.00", "400.00", "2832.00"),
        "gold": {"flags": ["GST_MISMATCH"]},
    },
    {
        "id": "CFS-B-201", "terminal": "Sample CFS Terminal B", "tariff_id": "SAMPLE_B",
        "text": invoice_text("Sample CFS Terminal B", "CFS-B-201", 20, "2026-10-02", "2026-10-05", [
            ("HANDLING", "Container handling", 2, "1200.00", "2600.00"),
            ("STORAGE", "Storage days", 1, "350.00", "350.00"),
            ("SEAL", "Seal charge", 1, "150.00", "150.00"),
        ], "3100.00", "558.00", "3658.00"),
        "gold": {"flags": ["ARITHMETIC", "NOT_IN_TARIFF"]},
    },
]


def write(name, value):
    DATA.mkdir(exist_ok=True)
    (DATA / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write("shipments.json", SHIPMENTS)
    write("questions.json", QUESTIONS)
    write("tariffs.json", TARIFFS)
    write("cfs_invoices.json", CFS)
    print(f"Wrote {len(SHIPMENTS)} shipments, {len(QUESTIONS)} questions, {len(TARIFFS)} tariffs, {len(CFS)} invoices.")
