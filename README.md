# kontenlaris — the agent-native CLI

One command line for every Kontenlaris Studio tool, built for **AI agents to call**: stable flags, JSON output (`--json`), meaningful exit codes, zero dependencies (Python ≥ 3.9 stdlib only).

```bash
pip install git+https://github.com/kontenlaris-studio/kontenlaris-cli
# or run in place:
python3 kontenlaris.py --help
```

| Command | What it does | Example |
|---|---|---|
| `invoice` | Invoice totals with discount & PPN, optional printable HTML | `kontenlaris invoice --item "Jasa Website:1:999000" --ppn 11 --out inv.html` |
| `ringkas` | Extractive summary (EN + ID), file or stdin | `cat article.txt \| kontenlaris ringkas --sentences 3` |
| `audit` | Security-scan an agent skill folder → A–F verdict | `kontenlaris audit ./some-skill --json` |
| `tokens` | Query the 838-protocol Pre-Token dataset (cached locally) | `kontenlaris tokens --category Lending --min-tvl 100000000` |

The engines are the same ones running in production: the InvoiceKit math, the RingkasBot summarizer (@KontenlarisRingkasBot), the SkillAudit scanner, and the [Pre-Token Protocols dataset](https://github.com/kontenlaris-studio/pre-token-protocols-dataset).

MIT · Kontenlaris Studio
