import React, { useEffect, useRef, useState } from "react";

export const planRequest = (plan) => ({
  ...(plan.ps2Semester ? { ps2_semester: plan.ps2Semester } : {}),
  auto_fill: plan.autoFill ?? true,
  bulletin_fallback: plan.bulletinFallback ?? false,
  allow_unconfirmed: plan.allowUnconfirmed ?? true,
  offering_overrides: plan.offeringOverrides || {},
  project_allocations: plan.projectAllocations || {},
  elective_allocations: plan.electiveAllocations || {},
  semester_assignments: plan.semesterAssignments || {},
  excluded_courses: plan.excludedCourses || [],
  heuristic: plan.heuristic || "composite",
  project_route: plan.projectRoute || "",
  branch: plan.branch,
  degree_type: plan.degreeType,
  minor: plan.minor || null,
  minor_core_choices: plan.minorCoreChoices?.[plan.minor] || [],
  current_semester: plan.planningMode === "transcript" ? plan.currentSemester : 0,
  target_semester: plan.targetSemester === 7 ? 7 : 8,
  max_credits: plan.maxCredits,
  completed_courses: plan.planningMode === "transcript" ? plan.completedCourses : [],
  selected_electives: plan.selectedElectives,
});
const label = (solver) => (solver === "astar" ? "A* Search" : "CSP");
const number = (value) =>
  Number.isFinite(value) ? value.toLocaleString() : "—";
const runtime = (result) =>
  Number.isFinite(result?.stats?.time_s)
    ? `${(result.stats.time_s * 1000).toFixed(2)} ms`
    : "—";
const finalTerm = (result) =>
  result?.status === "PLAN"
    ? Math.max(
        result.input.current_semester,
        ...Object.keys(result.semesters || {}).map(Number),
      )
    : null;

export default function SolverComparisonTab({
  plan,
  onUseResult,
  onComparison,
}) {
  const inputKey = JSON.stringify(planRequest(plan));
  const [results, setResults] = useState(plan.comparisonResults || {});
  const [running, setRunning] = useState(false);
  const [currentSolver, setCurrentSolver] = useState(null);
  const runId = useRef(0);
  const controller = useRef(null);
  useEffect(() => {
    runId.current += 1;
    controller.current?.abort();
    setResults(plan.comparisonResults || {});
    setRunning(false);
    setCurrentSolver(null);
    return () => {
      runId.current += 1;
      controller.current?.abort();
    };
  }, [inputKey, plan.id]);

  const compare = async () => {
    const id = ++runId.current;
    const input = JSON.parse(inputKey);
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    setResults({});
    setRunning(true);
    const measured = {};
    // Sequential runs avoid having both algorithms compete for CPU time.
    for (const solver of ["csp", "astar"]) {
      if (runId.current !== id) return;
      setCurrentSolver(solver);
      try {
        const response = await fetch("/api/plan", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: abort.signal,
          body: JSON.stringify({ ...input, solver }),
        });
        const data = await response.json();
        if (!response.ok)
          throw new Error(data.error || `Request failed (${response.status})`);
        if (runId.current !== id) return;
        measured[solver] = { ...data, input };
        setResults({ ...measured });
      } catch (error) {
        if (runId.current !== id || error.name === "AbortError") return;
        measured[solver] = { status: "ERROR", message: error.message, input };
        setResults({ ...measured });
      }
    }
    if (runId.current === id) {
      onComparison?.(measured);
      setRunning(false);
      setCurrentSolver(null);
    }
  };

  const columns = ["csp", "astar"];
  const rows = [
    ["Result", (r) => r?.status || "Not run"],
    ["Solver runtime", runtime],
    ["Search nodes", (r) => number(r?.stats?.nodes)],
    ["Backtracks (CSP)", (r) => number(r?.stats?.backtracks)],
    ["Semester bundles (A*)", (r) => number(r?.stats?.bundles)],
    ["Last scheduled semester", (r) => finalTerm(r) ?? "—"],
    [
      "Remaining semesters used",
      (r) =>
        r?.status === "PLAN" ? Object.keys(r.semesters || {}).length : "—",
    ],
    [
      "Planned credits",
      (r) => (r?.status === "PLAN" ? number(r.audit?.planned_credits) : "—"),
    ],
    [
      "Independent verification",
      (r) =>
        r
          ? r.verification_valid === true
            ? "Passed"
            : r.verification_valid === false
              ? "Failed"
              : "No plan to verify"
          : "—",
    ],
    [
      "Degree credit deficit",
      (r) => (r?.status === "PLAN" ? number(r.audit?.credit_deficit) : "—"),
    ],
  ];
  return (
    <section className="space-y-5">
      <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-3">
        <h2 className="text-lg font-bold">CSP vs A* Search</h2>
        <p className="text-sm text-slate-600">
          Run both algorithms on this plan with identical courses,
          prerequisites, credit caps, minor and graduation target. Each solver
          has a 15-second search limit.
        </p>
        <p className="text-xs text-slate-500">
          {plan.branch.toUpperCase()} · target {plan.targetSemester} ·{" "}
          {plan.maxCredits} credits per semester ·{" "}
          {plan.selectedElectives.length} selected electives
        </p>
        <button
          onClick={compare}
          disabled={running || plan.resultStatus !== "PLAN"}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-lg px-4 py-2 text-sm font-semibold"
        >
          {running ? `Running ${label(currentSolver)}…` : "Compare CSP and A*"}
        </button>
        <p className="text-xs text-slate-500" role="status" aria-live="polite">
          {running
            ? "Results appear as each solver finishes."
            : Object.keys(results).length
              ? "Comparison finished. Changing plan inputs clears these results."
              : "Generate a verified plan first, then run both solvers on its exact inputs."}
        </p>
      </div>
      <div className="overflow-x-auto bg-white border rounded-xl">
        <table className="w-full text-sm text-left">
          <thead className="bg-slate-100">
            <tr>
              <th className="p-3">Metric</th>
              {columns.map((s) => (
                <th key={s} className="p-3">
                  {label(s)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(([name, value]) => (
              <tr key={name} className="border-t">
                <th className="p-3 font-medium">{name}</th>
                {columns.map((s) => (
                  <td className="p-3" key={s}>
                    {value(results[s])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-500">
        CSP finds a feasible schedule. A* searches for fewer remaining semesters
        using a heuristic and a configured bundle limit; a returned plan does
        not establish global optimality. Runtime is measured inside each solver.
        Node definitions differ between algorithms. These are single runs, so
        timings can vary.
      </p>
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        {columns.map((solver) => {
          const result = results[solver];
          return (
            <article
              key={solver}
              className="bg-white rounded-xl border p-4 space-y-3 min-w-0"
            >
              <h3 className="font-bold">{label(solver)} schedule</h3>
              <p className="text-sm break-words">
                {result?.message || "Run the comparison to see this schedule."}
              </p>
              {result?.audit?.warning && (
                <p className="text-xs text-amber-800">{result.audit.warning}</p>
              )}
              {result?.status === "PLAN" && (
                <>
                  <button
                    disabled={running || result.verification_valid !== true}
                    onClick={() => onUseResult(solver, result)}
                    className="rounded-lg border border-blue-300 text-blue-700 px-3 py-2 text-xs font-semibold disabled:opacity-50"
                  >
                    Use {label(solver)} plan
                  </button>
                  <details>
                    <summary className="cursor-pointer text-sm font-semibold">
                      View semester courses
                    </summary>
                    {Object.values(result.semesters || {}).map((term) => (
                      <div key={term.semester} className="mt-3 border-t pt-2">
                        <h4 className="text-sm font-semibold">
                          Semester {term.semester} · {term.credits} Cr
                        </h4>
                        {term.courses.map((c) => (
                          <p key={c.code} className="text-xs mt-1 break-words">
                            <strong>{c.code}</strong> · {c.title} · {c.credits}{" "}
                            Cr
                          </p>
                        ))}
                      </div>
                    ))}
                    {Object.keys(result.semesters || {}).length === 0 && (
                      <p className="text-xs mt-2">
                        No remaining courses to schedule.
                      </p>
                    )}
                  </details>
                </>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
