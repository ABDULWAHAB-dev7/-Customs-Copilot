"""Tool B: read a CFS invoice and check it against a tariff card. All money in Decimal."""
import re
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")
LINE = re.compile(r"^LINE (\d+) \| (\w+) \| ([^|]+?) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+)$")
HEADER_KEYS = {"TERMINAL", "INVOICE NO", "CONTAINER", "SIZE", "GATE IN", "GATE OUT"}
FOOTER_KEYS = {"SUBTOTAL", "GST", "TOTAL"}


class ReadError(Exception):
    pass


class TariffError(Exception):
    pass


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def fmt(value):
    return f"{money(value):.2f}"


def read_invoice(text):
    header, footer, lines = {}, {}, []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = LINE.match(line)
        if m:
            n, code, desc, qty, rate, amount = m.groups()
            try:
                lines.append({
                    "line": int(n), "code": code, "description": desc.strip(),
                    "qty": Decimal(qty), "rate": money(rate), "amount": money(amount),
                })
            except ArithmeticError:
                raise ReadError(f"LINE {n} quantity, rate and amount must be plain numbers.")
            continue
        key, sep, value = line.partition(":")
        key = key.strip().upper()
        if not sep:
            continue
        if key in HEADER_KEYS:
            header[key] = value.strip()
        elif key in FOOTER_KEYS:
            footer[key] = value.strip()

    missing = [k for k in HEADER_KEYS | FOOTER_KEYS if k not in header and k not in footer]
    if missing or not lines:
        raise ReadError("Invoice layout not recognised: missing " + ", ".join(sorted(missing or ["LINE rows"])))
    try:
        gate_in = date.fromisoformat(header["GATE IN"])
        gate_out = date.fromisoformat(header["GATE OUT"])
        subtotal, gst, total = money(footer["SUBTOTAL"]), money(footer["GST"]), money(footer["TOTAL"])
    except (ValueError, ArithmeticError):
        raise ReadError("SUBTOTAL, GST and TOTAL must be amounts, and GATE IN and GATE OUT must be YYYY-MM-DD dates.")
    if gate_out < gate_in:
        raise ReadError("GATE OUT is before GATE IN.")

    return {
        "terminal": header["TERMINAL"],
        "invoice_no": header["INVOICE NO"],
        "container": header["CONTAINER"],
        "size": header["SIZE"],
        "gate_in": gate_in,
        "gate_out": gate_out,
        "lines": lines,
        "subtotal": subtotal,
        "gst": gst,
        "total": total,
    }


def select_tariff(tariffs, tariff_id, terminal):
    if tariff_id:
        if tariff_id not in tariffs:
            raise TariffError(f"No tariff card named '{tariff_id}'.")
        return tariff_id, tariffs[tariff_id]
    for tid, card in tariffs.items():
        if card["terminal"] == terminal:
            return tid, card
    raise TariffError(f"No tariff card exists for terminal '{terminal}'.")


def slab_amount(storage, size, days):
    bands = storage["slabs"].get(size)
    if bands is None:
        raise TariffError(f"No storage slabs for container size {size}.")
    total = Decimal("0")
    for day in range(1, days + 1):
        for lo, hi, rate in bands:
            if day >= lo and (hi is None or day <= hi):
                total += Decimal(rate)
                break
    return money(total)


def flag(code, line, message, tariff_ref, billed, expected, overcharge):
    return {
        "code": code, "line": line, "message": message, "tariff_ref": tariff_ref,
        "billed": billed, "expected": expected, "overcharge": overcharge,
    }


def check(inv, card):
    flags = []
    size = inv["size"]
    charges = card["charges"]
    storage = card["storage"]
    seen = set()
    storage_seen = False
    line_over = {}

    for ln in inv["lines"]:
        code, n = ln["code"], ln["line"]
        expected_amount = money(ln["qty"] * ln["rate"])
        if abs(ln["amount"] - expected_amount) > CENT:
            over = max(Decimal("0"), ln["amount"] - expected_amount)
            flags.append(flag("ARITHMETIC", n, f"Quantity times rate is {fmt(expected_amount)}, not {fmt(ln['amount'])}.",
                              "Line arithmetic", fmt(ln["amount"]), fmt(expected_amount), fmt(over)))

        if code == "STORAGE":
            if storage_seen:
                flags.append(flag("DUPLICATE", n, "A second storage line is billed; storage is checked once per invoice.",
                                  "Duplicate storage", fmt(ln["amount"]), "0.00", fmt(ln["amount"])))
                line_over[n] = ln["amount"]
            storage_seen = True
            continue

        key = (code, ln["description"], ln["amount"])
        if key in seen:
            flags.append(flag("DUPLICATE", n, f"{code} {ln['description']} for {fmt(ln['amount'])} appears more than once.",
                              "Duplicate line", fmt(ln["amount"]), "0.00", fmt(ln["amount"])))
            line_over[n] = ln["amount"]
        seen.add(key)

        if code not in charges:
            flags.append(flag("NOT_IN_TARIFF", n, f"{code} is not on the tariff card.",
                              "Not in tariff", fmt(ln["amount"]), "0.00", fmt(ln["amount"])))
            line_over[n] = ln["amount"]
            continue

        rates = charges[code]["rate"]
        if size not in rates:
            raise TariffError(f"Tariff card has no {code} rate for container size {size}.")
        exp_rate = money(rates[size])
        if ln["rate"] != exp_rate:
            over = max(Decimal("0"), (ln["rate"] - exp_rate) * ln["qty"])
            flags.append(flag("RATE_MISMATCH", n,
                              f"Billed rate {fmt(ln['rate'])} for a {size} ft container; card says {fmt(exp_rate)}.",
                              f"{code} rate {size} ft", fmt(ln["rate"]), fmt(exp_rate), fmt(over)))
        line_over.setdefault(n, max(Decimal("0"), ln["amount"] - money(ln["qty"] * exp_rate)))

    free = storage["free_days"]
    dwell = (inv["gate_out"] - inv["gate_in"]).days
    chargeable = max(0, dwell - free)
    storage_lines = [ln for ln in inv["lines"] if ln["code"] == "STORAGE"]
    billed_days = int(storage_lines[0]["qty"]) if storage_lines else 0
    billed_amount = storage_lines[0]["amount"] if storage_lines else Decimal("0")
    exp_amount = slab_amount(storage, size, chargeable)
    storage_over = max(Decimal("0"), billed_amount - exp_amount)
    if storage_lines:
        line_over[storage_lines[0]["line"]] = storage_over
    if billed_days != chargeable or billed_amount != exp_amount:
        flags.append(flag("STORAGE_DAYS", storage_lines[0]["line"] if storage_lines else None,
                          f"Billed {billed_days} storage days; {dwell} days dwell less {free} free days leaves {chargeable}.",
                          f"Free days: {free}",
                          f"{billed_days} days / {fmt(billed_amount)}",
                          f"{chargeable} days / {fmt(exp_amount)}",
                          fmt(storage_over)))

    sub_calc = money(sum((ln["amount"] for ln in inv["lines"]), Decimal("0")))
    gst_pct = Decimal(card["gst_percent"])
    gst_calc = money(sub_calc * gst_pct / Decimal("100"))
    total_calc = money(sub_calc + gst_calc)
    if inv["subtotal"] != sub_calc:
        flags.append(flag("SUBTOTAL_MISMATCH", None, f"Lines add to {fmt(sub_calc)}, footer says {fmt(inv['subtotal'])}.",
                          "Subtotal", fmt(inv["subtotal"]), fmt(sub_calc), "0.00"))
    if inv["gst"] != gst_calc:
        flags.append(flag("GST_MISMATCH", None, f"GST at {card['gst_percent']}% is {fmt(gst_calc)}, footer says {fmt(inv['gst'])}.",
                          f"GST {card['gst_percent']}%", fmt(inv["gst"]), fmt(gst_calc), "0.00"))
    if inv["total"] != total_calc:
        flags.append(flag("TOTAL_MISMATCH", None, f"Total should be {fmt(total_calc)}, footer says {fmt(inv['total'])}.",
                          "Total", fmt(inv["total"]), fmt(total_calc), "0.00"))

    return flags, dwell, sum(line_over.values(), Decimal("0"))


def check_invoice(text, tariffs, tariff_id=None):
    inv = read_invoice(text)
    tid, card = select_tariff(tariffs, tariff_id, inv["terminal"])
    flags, dwell, over = check(inv, card)
    if flags:
        explanation = (f"{len(flags)} check(s) disagree with tariff card {tid}. "
                       f"Overcharge before GST: {fmt(over)}. Each flag names the tariff line it was compared with.")
    else:
        explanation = f"No discrepancies against tariff card {tid}. Lines, storage days and footer totals agree."
    return {
        "terminal": inv["terminal"],
        "dwell_days": dwell,
        "read_with": "regex",
        "flags": flags,
        "overcharge_before_gst": fmt(over),
        "explanation": explanation,
        "parsed": {
            "invoice_no": inv["invoice_no"],
            "container": inv["container"],
            "size": inv["size"],
            "gate_in": inv["gate_in"].isoformat(),
            "gate_out": inv["gate_out"].isoformat(),
            "lines": [
                {"line": ln["line"], "code": ln["code"], "description": ln["description"],
                 "qty": str(ln["qty"]), "rate": fmt(ln["rate"]), "amount": fmt(ln["amount"])}
                for ln in inv["lines"]
            ],
            "subtotal": fmt(inv["subtotal"]),
            "gst": fmt(inv["gst"]),
            "total": fmt(inv["total"]),
        },
    }
