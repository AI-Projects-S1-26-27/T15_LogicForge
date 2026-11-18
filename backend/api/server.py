"""GraphMind — API Server for React UI
Provides clean REST endpoints using Python's standard library ThreadingHTTPServer.
Handles CORS, degree constraints, plan generation, verification, and credit auditing.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse, unquote

# Ensure project root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


class RequestHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.OK)
        self._send_cors_headers()
        self.end_headers()

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, indent=2, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/health":
            self._send_json(
                {
                    "status": "healthy",
                    "service": "GraphMind Planner API",
                    "revision": "2026.11.18-r17",
                }
            )
            return

        if path == "/api/curriculum":
            from backend.services.scoped_planner import curriculum_response, InputError

            try:
                data = curriculum_response(
                    query.get("branch", ["cse"])[0], query.get("minor", [None])[0]
                )
                self._send_json(data)
            except InputError as exc:
                self._send_json({"error": str(exc), "issues": exc.issues}, status=400)
            return

        if path == "/api/heuristics/explain":
            from backend.ml.predict import model_info

            data = {
                "model": model_info(),
                "title": "A* heuristic options",
                "learned_model": "Bundled 6-input, 16/8-hidden-unit MLP",
                "comparison": [
                    {
                        "heuristic": "composite",
                        "formula": "max(credit bound, prerequisite critical path, availability bound)",
                        "admissible": True,
                    },
                    {
                        "heuristic": "learned",
                        "formula": "composite primary f score; MLP orders equal-f, equal-depth states",
                        "admissible": False,
                        "limitation": "Experimental prediction; no guaranteed speedup or optimality. Missing model falls back to composite.",
                    },
                ],
            }
            self._send_json(data)
            return

        if path.startswith("/api/"):
            self._send_json({"error": "Endpoint not found"}, status=404)
            return

        # Serve static build from frontend/dist
        dist_dir = os.path.join(REPO_ROOT, "frontend", "dist")
        if os.path.isdir(dist_dir):
            clean_path = unquote(path).lstrip("/")
            if not clean_path or clean_path == "/":
                clean_path = "index.html"
            file_path = os.path.realpath(os.path.join(dist_dir, clean_path))
            if os.path.commonpath(
                [os.path.realpath(dist_dir), file_path]
            ) != os.path.realpath(dist_dir):
                self._send_json({"error": "Invalid asset path"}, status=400)
                return
            if not os.path.exists(file_path) and clean_path.startswith("assets/"):
                self._send_json(
                    {"error": "Asset not found; refresh the dashboard"}, status=404
                )
                return
            if not os.path.exists(file_path):
                file_path = os.path.join(dist_dir, "index.html")

            if os.path.isfile(file_path):
                content_type = "text/html"
                if file_path.endswith(".js"):
                    content_type = "application/javascript"
                elif file_path.endswith(".css"):
                    content_type = "text/css"
                elif file_path.endswith(".jpg") or file_path.endswith(".jpeg"):
                    content_type = "image/jpeg"
                elif file_path.endswith(".png"):
                    content_type = "image/png"
                elif file_path.endswith(".svg"):
                    content_type = "image/svg+xml"

                with open(file_path, "rb") as f:
                    body = f.read()
                self.send_response(HTTPStatus.OK)
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(body)
                return

        self._send_json({"error": "Endpoint not found"}, status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/feedback":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                fb = json.loads(post_data.decode("utf-8"))
                fb_path = os.path.join(
                    REPO_ROOT, "experiments", "results", "e5_feedback.csv"
                )
                os.makedirs(os.path.dirname(fb_path), exist_ok=True)
                new_f = not os.path.exists(fb_path)
                with open(fb_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    if new_f:
                        writer.writerow(
                            [
                                "timestamp",
                                "solver",
                                "status",
                                "correct",
                                "useful",
                                "comment",
                            ]
                        )
                    writer.writerow(
                        [
                            fb.get("timestamp", ""),
                            fb.get("solver", "csp"),
                            fb.get("status", "PLAN"),
                            fb.get("correct", "Yes"),
                            fb.get("useful", 5),
                            fb.get("comment", ""),
                        ]
                    )
                self._send_json({"status": "ok", "message": "Feedback saved"})
            except Exception as e:
                self._send_json(
                    {"error": f"Failed to save feedback: {str(e)}"}, status=400
                )
            return

        if parsed.path not in ("/api/plan", "/api/feasibility", "/api/schedule/edit"):
            self._send_json({"error": "Endpoint not found"}, status=404)
            return

        from backend.services.scoped_api import plan_payload
        from backend.services.scoped_planner import InputError

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1000000:
                raise InputError("Request body must be from 1 byte to 1 MB.")
            req = json.loads(self.rfile.read(length).decode("utf-8"))
            if parsed.path == "/api/schedule/edit":
                from backend.services.scoped_api import edit_payload

                self._send_json(edit_payload(req))
            elif parsed.path == "/api/feasibility":
                from backend.services.scoped_planner import normalize_request

                normalized = normalize_request(req)
                rows = []
                for target in (7, 8):
                    try:
                        outcome = plan_payload(
                            {**normalized, "target_semester": target, "solver": "csp"}
                        )
                        rows.append(
                            {
                                "target": target,
                                "status": outcome["status"],
                                "requirements_met": outcome["audit"][
                                    "requirements_met"
                                ],
                                "verified": outcome["verification_valid"],
                                "credits": outcome["audit"]["total_credits_planned"],
                                "message": outcome["message"],
                            }
                        )
                    except InputError as exc:
                        rows.append(
                            {
                                "target": target,
                                "status": "INPUT_BLOCKED",
                                "message": str(exc),
                                "issues": exc.issues,
                            }
                        )
                first = next(
                    (
                        r["target"]
                        for r in rows
                        if r.get("verified") and r.get("requirements_met")
                    ),
                    None,
                )
                self._send_json(
                    {
                        "results": rows,
                        "earliest_verified_target": first,
                        "note": "Earliest among tested targets for the concrete recommendation set and source assumptions; not an exhaustive academic acceleration guarantee.",
                    }
                )
            else:
                self._send_json(plan_payload(req))
        except InputError as exc:
            self._send_json({"error": str(exc), "issues": exc.issues}, status=400)
        except (ValueError, TypeError, UnicodeDecodeError):
            self._send_json({"error": "Invalid JSON request."}, status=400)
        except Exception as exc:
            self._send_json({"error": f"Planner could not complete: {exc}"}, status=500)


def run_server(port: int = 8000, on_ready=None):
    server_address = ("127.0.0.1", port)
    httpd = ThreadingHTTPServer(server_address, RequestHandler)
    print(f"GraphMind 2026.11.18-r17 running at http://127.0.0.1:{port}", flush=True)
    if on_ready:
        on_ready(port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping API server...")
        httpd.server_close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port)
