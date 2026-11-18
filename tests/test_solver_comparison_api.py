"""Compare both real algorithms through the same HTTP contract used by the UI."""

import json
import threading
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
import pytest
from backend.api.server import RequestHandler
from backend.services.scoped_planner import DATA


@pytest.fixture
def api_url():
    server = ThreadingHTTPServer(("127.0.0.1", 0), RequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/api/plan"
    server.shutdown()
    server.server_close()
    thread.join()


def test_both_solvers_receive_identical_input_and_return_verified_schedules(api_url):
    courses = DATA["common"] + [
        c for c, sem in DATA["branches"]["cse"]["patterns"].items() if sem == 3
    ]
    payload = dict(
        branch="cse",
        degree_type="single",
        current_semester=3,
        target_semester=8,
        max_credits=22,
        completed_courses=[c for c in courses if c != "CS F211"],
        selected_electives=["HSS F222"],
        bulletin_fallback=True,
    )
    outputs = {}
    for solver in ("csp", "astar"):
        request = Request(
            api_url,
            data=json.dumps(dict(payload, solver=solver)).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(request, timeout=30) as response:
            outputs[solver] = json.load(response)
        result = outputs[solver]
        assert result["solver"] == solver
        assert result["status"] == "PLAN", result["message"]
        assert result["verification_valid"] is True
        assert result["stats"]["time_s"] >= 0
        assert result["stats"]["nodes"] >= 0
        scheduled = [
            c["code"] for term in result["semesters"].values() for c in term["courses"]
        ]
        assert "CS F211" in scheduled
        assert "HSS F222" in scheduled
        assert all(term["credits"] <= 22 for term in result["semesters"].values())
    assert "backtracks" in outputs["csp"]["stats"]
    assert "bundles" in outputs["astar"]["stats"]
    scheduled = lambda result: {
        c["code"] for t in result["semesters"].values() for c in t["courses"]
    }
    assert scheduled(outputs["csp"]) == scheduled(outputs["astar"])


def test_catalogue_http_contract_and_unknown_route(api_url):
    from urllib.error import HTTPError

    base = api_url.removesuffix("/api/plan")
    with urlopen(base + "/api/curriculum?branch=eee&minor=finance") as response:
        data = json.load(response)
    assert len(data["all_courses"]) == 384
    assert len(data["minors"]) == 5
    assert data["selected_minor"]["name"] == "Finance"
    assert len(data["catalogue_signature"]) == 64
    for path, status in [
        ("/api/not-real", 404),
        ("/%2e%2e/%2e%2e/README.md", 400),
        ("/assets/not-real.js", 404),
    ]:
        with pytest.raises(HTTPError) as caught:
            urlopen(base + path)
        assert caught.value.code == status


def test_feasibility_http_runs_the_same_candidate_set(api_url):
    payload = dict(
        branch="cse",
        current_semester=2,
        target_semester=8,
        completed_courses=DATA["common"],
        project_route="practice_school",
        max_credits=25,
    )
    request = Request(
        api_url.replace("/api/plan", "/api/feasibility"),
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=30) as response:
        data = json.load(response)
    assert [r["target"] for r in data["results"]] == [7, 8]
    assert data["earliest_verified_target"] == 7
    assert data["results"][0]["status"] == "PLAN"
