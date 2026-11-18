"""Rebuild timetable evidence for the curated screenshot catalogue.
Usage: python scripts/ingest_offerings.py --odd ODD.pdf --even EVEN.pdf
Requires Poppler's pdftotext only for this optional ingestion step.
The runnable app has no PDF-parsing dependency.
"""

import argparse, hashlib, json, re, subprocess
from pathlib import Path


def extract(text):
    evidence = {}
    for page_no, page in enumerate(text.split("\f"), 1):
        # One PDF has no standalone TEXT BOOK title. Its table header is the boundary.
        if re.search(r"COURSE\s+TITLE[^\n]*TEXT\s*BOOK", page, re.I) or re.search(
            r"^\s*TEXT\s*BOOKS?\s*$", page, re.M | re.I
        ):
            break
        for line_no, line in enumerate(page.splitlines(), 1):
            for m in re.finditer(r"\b([A-Z]{2,6})\s+([FG]\s*\d{3}T?)\b", line):
                code = m[1] + " " + re.sub(r"\s", "", m[2])
                evidence.setdefault(
                    code,
                    {
                        "page": page_no,
                        "line": line_no,
                        "excerpt": line.strip()[:160],
                        "evidence_type": "Teaching timetable",
                    },
                )
    return evidence


def update(data, texts):
    parsed = {term: extract(text) for term, text in texts.items()}
    for code, c in data["courses"].items():
        evidence = {term: rows[code] for term, rows in parsed.items() if code in rows}
        if code == "BITS F412":
            for term, text in texts.items():
                for n, page in enumerate(text.split("\f")[:3], 1):
                    matches = [
                        l.strip()
                        for l in page.splitlines()
                        if re.search(r"Practice\s+School\s*II", l, re.I)
                    ]
                    if matches:
                        evidence[term] = {
                            "page": n,
                            "excerpt": matches[0][:160],
                            "evidence_type": "Academic calendar placement registration; programme pattern identifies BITS F412",
                        }
                        break
        c["offering_evidence"] = evidence
        c["offered_terms"] = list(evidence)
        c["offering_status"] = (
            "both" if len(evidence) == 2 else next(iter(evidence), "unconfirmed")
        )
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--odd", type=Path, required=True)
    parser.add_argument("--even", type=Path, required=True)
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[1] / "data/curriculum/scoped_catalogue.json"
    data = json.loads(path.read_text())
    texts = {
        term: subprocess.run(
            ["pdftotext", "-layout", str(pdf), "-"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        for term, pdf in [("odd", args.odd), ("even", args.even)]
    }
    data = update(data, texts)
    for term, pdf in [("odd", args.odd), ("even", args.even)]:
        data["sources"][term]["sha256"] = hashlib.sha256(pdf.read_bytes()).hexdigest()
        data["sources"][term]["file"] = pdf.name
        year = re.search(r"((?:19|20)\d{2})\s*-\s*(\d{2})", pdf.name)
        if year:
            data["sources"][term][
                "snapshot"
            ] = f"{year[1]}-{year[2]} Semester {'I' if term == 'odd' else 'II'}"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    print(
        {
            s: sum(c["offering_status"] == s for c in data["courses"].values())
            for s in ("odd", "even", "both", "unconfirmed")
        }
    )


if __name__ == "__main__":
    main()
