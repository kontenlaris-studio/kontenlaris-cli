#!/usr/bin/env python3
"""kontenlaris — the agent-native CLI for Kontenlaris Studio tools.

Every command prints machine-readable output (JSON with --json, plain
otherwise) and exits non-zero on error, so AI agents can call it safely.

Commands:
  invoice   Build an invoice (totals, PPN, discount) + optional HTML
  ringkas   Extractive summary of a text file or stdin (EN + ID)
  audit     Security-scan an agent skill folder (A-F verdict)
  tokens    Query the Pre-Token Protocols dataset (838 protocols)
"""
import argparse, json, os, sys, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kontenlaris_cli.summarizer import summarize
from kontenlaris_cli import audit_engine

DATASET_URL = ("https://raw.githubusercontent.com/kontenlaris-studio/"
               "pre-token-protocols-dataset/main/data/pre_token_protocols.jsonl")
CACHE = os.path.expanduser("~/.cache/kontenlaris/tokens.jsonl")


def rp(n):
    return "Rp" + f"{int(round(n)):,}".replace(",", ".")


def cmd_invoice(a):
    items = []
    for spec in a.item or []:
        parts = spec.rsplit(":", 2)
        if len(parts) != 3:
            raise SystemExit(f"bad --item format (want Name:qty:unit_price): {spec}")
        name, qty, price = parts[0], float(parts[1]), float(parts[2])
        items.append({"name": name, "qty": qty, "unit_price": price,
                      "amount": qty * price})
    subtotal = sum(i["amount"] for i in items)
    discount = subtotal * (a.discount or 0) / 100.0
    taxable = subtotal - discount
    ppn = taxable * (a.ppn or 0) / 100.0
    total = taxable + ppn
    inv = {"number": a.number or "INV/CLI/001", "seller": a.seller or "",
           "buyer": a.buyer or "", "items": items, "subtotal": subtotal,
           "discount_pct": a.discount or 0, "discount": discount,
           "ppn_pct": a.ppn or 0, "ppn": ppn, "total": total,
           "total_formatted": rp(total)}
    if a.out:
        rows = "".join(
            f"<tr><td>{i['name']}</td><td>{i['qty']:g}</td>"
            f"<td>{rp(i['unit_price'])}</td><td>{rp(i['amount'])}</td></tr>"
            for i in items)
        html = f"""<!doctype html><meta charset="utf-8"><title>{inv['number']}</title>
<style>body{{font:15px system-ui;max-width:720px;margin:40px auto;color:#14213d}}
table{{width:100%;border-collapse:collapse}}td,th{{border-bottom:1px solid #ddd;padding:8px;text-align:left}}
td:last-child,th:last-child{{text-align:right}}h1{{color:#0a1931}}.tot{{font-weight:800;font-size:18px}}</style>
<h1>INVOICE {inv['number']}</h1><p>{inv['seller']} &rarr; {inv['buyer']}</p>
<table><tr><th>Item</th><th>Qty</th><th>Price</th><th>Amount</th></tr>{rows}
<tr><td colspan="3">Subtotal</td><td>{rp(subtotal)}</td></tr>
<tr><td colspan="3">Discount ({inv['discount_pct']:g}%)</td><td>-{rp(discount)}</td></tr>
<tr><td colspan="3">PPN ({inv['ppn_pct']:g}%)</td><td>{rp(ppn)}</td></tr>
<tr class="tot"><td colspan="3">TOTAL</td><td>{rp(total)}</td></tr></table>"""
        open(a.out, "w").write(html)
        inv["html_written"] = a.out
    print(json.dumps(inv, indent=2) if a.json else
          f"{inv['number']}: total {inv['total_formatted']} "
          f"({len(items)} items, PPN {inv['ppn_pct']:g}%)")
    return 0


def cmd_ringkas(a):
    text = sys.stdin.read() if a.file in (None, "-") else open(a.file).read()
    out = summarize(text, max_sentences=a.sentences)
    print(json.dumps({"summary": out}, ensure_ascii=False, indent=2)
          if a.json else out)
    return 0


def cmd_audit(a):
    findings, domains, files = audit_engine.audit(a.path)
    report = audit_engine.to_markdown(a.path, findings, domains, files)
    if a.json:
        g = audit_engine.grade(findings).split(" ")[0]
        print(json.dumps({"grade": g, "findings": len(findings),
                          "domains": sorted(domains)}, indent=2))
    else:
        print(report)
    return 0


def load_tokens(a):
    if a.file:
        raw = open(a.file).read()
    else:
        if not os.path.exists(CACHE):
            os.makedirs(os.path.dirname(CACHE), exist_ok=True)
            with urllib.request.urlopen(DATASET_URL, timeout=30) as r:
                data = r.read().decode()
            open(CACHE, "w").write(data)
        raw = open(CACHE).read()
    return [json.loads(l) for l in raw.splitlines() if l.strip()]


def cmd_tokens(a):
    rows = load_tokens(a)
    if a.category:
        rows = [r for r in rows if a.category.lower()
                in str(r.get("category", "")).lower()]
    if a.min_tvl:
        rows = [r for r in rows if float(r.get("tvl_usd") or 0) >= a.min_tvl]
    if a.search:
        rows = [r for r in rows if a.search.lower()
                in str(r.get("name", "")).lower()]
    rows.sort(key=lambda r: float(r.get("tvl_usd") or 0), reverse=True)
    rows = rows[: a.limit]
    if a.json:
        print(json.dumps(rows, indent=2))
    else:
        for r in rows:
            print(f"{r.get('name','?'):<28} {str(r.get('category','')):<18} "
                  f"TVL ${float(r.get('tvl_usd') or 0):,.0f}")
        print(f"-- {len(rows)} protocols")
    return 0


def main():
    p = argparse.ArgumentParser(prog="kontenlaris", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    i = sub.add_parser("invoice", help="build an invoice")
    i.add_argument("--item", action="append",
                   help="Name:qty:unit_price (repeatable)")
    i.add_argument("--seller"); i.add_argument("--buyer")
    i.add_argument("--number"); i.add_argument("--ppn", type=float, default=0)
    i.add_argument("--discount", type=float, default=0)
    i.add_argument("--out", help="write a printable HTML invoice")
    i.add_argument("--json", action="store_true")
    i.set_defaults(fn=cmd_invoice)

    r = sub.add_parser("ringkas", help="summarize text (file or stdin)")
    r.add_argument("file", nargs="?")
    r.add_argument("--sentences", type=int, default=3)
    r.add_argument("--json", action="store_true")
    r.set_defaults(fn=cmd_ringkas)

    au = sub.add_parser("audit", help="security-scan a skill folder")
    au.add_argument("path")
    au.add_argument("--json", action="store_true")
    au.set_defaults(fn=cmd_audit)

    t = sub.add_parser("tokens", help="query the pre-token dataset")
    t.add_argument("--category"); t.add_argument("--search")
    t.add_argument("--min-tvl", type=float, default=0)
    t.add_argument("--limit", type=int, default=10)
    t.add_argument("--file", help="use a local JSONL instead of fetching")
    t.add_argument("--json", action="store_true")
    t.set_defaults(fn=cmd_tokens)

    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
