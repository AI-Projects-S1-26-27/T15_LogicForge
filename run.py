"""Single-command launcher for the submitted, prebuilt dashboard."""

from __future__ import annotations
import argparse, errno, json, sys
from pathlib import Path


def preflight():
    from backend.services.scoped_planner import DATA, MINORS, CATALOGUE_SIGNATURE
    from backend.ml.predict import model_info

    root = Path(__file__).resolve().parent
    if not (root / "frontend/dist/index.html").is_file():
        raise RuntimeError(
            "Compiled dashboard missing. Run npm ci && npm run build in frontend/."
        )
    for branch, row in DATA["branches"].items():
        referenced = set(row["core"] + row["electives"]) | {
            c for g in row["alternative_core_groups"] for c in g
        }
        if referenced - DATA["courses"].keys():
            raise RuntimeError(f"Unresolved branch catalogue: {branch}")
    for minor in MINORS.values():
        referenced = set(minor["core"] + minor["electives"]) | {
            c for g in minor["core_alternatives"] for c in g
        }
        if referenced - DATA["courses"].keys():
            raise RuntimeError(f'Unresolved minor: {minor["id"]}')
    if any(
        not isinstance(c["credits"], int) or c["credits"] <= 0
        for c in DATA["courses"].values()
    ):
        raise RuntimeError("Invalid units in catalogue.")
    model = model_info()
    return {
        "status": "ready",
        "learned_model_available": model["available"],
        "courses": len(DATA["courses"]),
        "branches": len(DATA["branches"]),
        "minors": len(MINORS),
        "availability": {
            s: sum(c["offering_status"] == s for c in DATA["courses"].values())
            for s in ("odd", "even", "both", "unconfirmed")
        },
        "catalogue_signature": CATALOGUE_SIGNATURE,
        "runtime": "Python standard library + included React build and neural weights",
    }


def open_browser(port):
    """Open only after this newly bound server responds, never an old port's UI."""
    import threading
    import time
    import urllib.request
    import webbrowser

    def ready():
        url = f"http://127.0.0.1:{port}"
        for _ in range(25):
            try:
                with urllib.request.urlopen(url + "/api/health", timeout=1) as response:
                    if response.status == 200:
                        webbrowser.open(url)
                        return
            except OSError:
                time.sleep(0.2)
        print(f"Open {url} in your browser.", flush=True)

    threading.Thread(target=ready, daemon=True).start()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the new dashboard in your browser; try the next available port if occupied.",
    )
    args = parser.parse_args()
    try:
        status = preflight()
        if args.check:
            print(json.dumps(status, indent=2))
            return
        if not 1024 <= args.port <= 65535:
            raise ValueError("Choose a port from 1024 to 65535.")
        from backend.api.server import run_server

        for port in range(args.port, min(65536, args.port + (20 if args.open else 1))):
            try:
                run_server(port, on_ready=open_browser if args.open else None)
                return
            except OSError as error:
                if not args.open or error.errno != errno.EADDRINUSE:
                    raise
        raise RuntimeError("No free port found. Close an old server or choose --port.")
    except (RuntimeError, ValueError, OSError) as exc:
        print(
            f"Could not start GraphMind: {exc}\nIf the port is in use, try python run.py --port 8001.",
            file=sys.stderr,
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
