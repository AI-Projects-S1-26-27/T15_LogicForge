import React, { useState } from "react";
export default function ComparePlansTab({
  plans,
  activePlanId,
  onSelectPlan,
  onDeletePlan,
  onDuplicate,
  onRename,
}) {
  const [deleting, setDeleting] = useState(null);
  return (
    <section className="space-y-4">
      <div>
        <h1 className="text-xl font-bold">Saved plans</h1>
        <p className="text-sm text-slate-500 mt-1">
          Compare settings, duplicate a scenario or export a portable backup.
          Importing plans never imports a verified result.
        </p>
      </div>
      <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
        {plans.map((p) => (
          <article
            key={p.id}
            className={`bg-white border rounded-xl p-4 space-y-4 ${p.id === activePlanId ? "border-blue-400" : ""}`}
          >
            <label className="text-xs text-slate-500">
              Plan name
              <input
                aria-label={`Name ${p.id}`}
                value={p.name}
                maxLength={80}
                onChange={(e) => onRename(p.id, e.target.value)}
                className="block w-full border rounded-lg p-2 mt-1 text-sm text-slate-800"
              />
            </label>
            <dl className="grid grid-cols-2 text-xs gap-2">
              <dt>Branch</dt>
              <dd>{p.branch.toUpperCase()}</dd>
              <dt>Target</dt>
              <dd>Semester {p.targetSemester}</dd>
              <dt>Credit cap</dt>
              <dd>{p.maxCredits}</dd>
              <dt>Algorithm</dt>
              <dd>
                {p.solver === "csp"
                  ? "CSP"
                  : `A* / ${p.heuristic || "composite"}`}
              </dd>
              <dt>Minor</dt>
              <dd className="break-words">
                {p.minor?.replaceAll("_", " ") || "None"}
              </dd>
              <dt>Explicit electives</dt>
              <dd>{p.selectedElectives.length}</dd>
            </dl>
            <p className="text-xs rounded-lg bg-slate-50 p-3">
              {p.audit
                ? `${p.resultStatus} · ${p.audit.total_credits_planned} planned units · ${p.audit.graduation_assessment}`
                : "Not generated for these inputs."}
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => onSelectPlan(p.id)}
                className="text-xs rounded-lg border px-3 py-2"
              >
                {p.id === activePlanId ? "Open active plan" : "Load plan"}
              </button>
              <button
                onClick={() => onDuplicate(p.id)}
                className="text-xs rounded-lg border px-3 py-2"
              >
                Duplicate
              </button>
              {deleting === p.id ? (
                <>
                  <button
                    onClick={() => {
                      onDeletePlan(p.id);
                      setDeleting(null);
                    }}
                    className="text-xs rounded-lg bg-red-50 text-red-700 border px-3 py-2"
                  >
                    Confirm delete
                  </button>
                  <button
                    onClick={() => setDeleting(null)}
                    className="text-xs px-3 py-2"
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <button
                  disabled={plans.length <= 1}
                  onClick={() => setDeleting(p.id)}
                  className="text-xs rounded-lg border px-3 py-2 disabled:opacity-40"
                >
                  Delete
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
