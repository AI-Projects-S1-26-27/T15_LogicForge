import React from "react";
const numeric = (v, digits = 2) =>
  Number.isFinite(v) ? v.toFixed(digits) : "—";
const cell = (v) =>
  typeof v === "string" || typeof v === "number" ? String(v) : "—";
export default function HeuristicExplainerTab({
  plan = {},
  onChoose = () => {},
  onHome = () => {},
}) {
  const details = plan?.stats?.heuristic_details;
  const features =
    details?.features &&
    typeof details.features === "object" &&
    !Array.isArray(details.features)
      ? Object.entries(details.features)
      : [];
  return (
    <section className="space-y-6">
      <div className="page-heading">
        <div>
          <p className="eyebrow">A little intelligence, a clearer path</p>
          <h1>How learned guidance works.</h1>
          <p>
            A* chooses which partial schedule to explore next. The neural model
            helps order equally ranked choices.
          </p>
        </div>
        <button className="secondary-action" onClick={onHome}>
          Back to semester plan
        </button>
      </div>
      <div className="explanation-grid">
        <article className="explanation-card">
          <span className="step-tag">01 · The primary score</span>
          <h2>Keep the lower bound.</h2>
          <p>
            A* uses semesters already used + a composite lower bound on
            semesters remaining. That bound includes credits, prerequisite depth
            and offering windows.
          </p>
        </article>
        <article className="explanation-card accent-card">
          <span className="step-tag">02 · Learned ordering</span>
          <h2>Use the model to break ties.</h2>
          <p>
            A six-feature MLP predicts remaining terms. Among states with equal
            f score and depth, the prediction orders exploration. It never
            changes your degree requirements or overrides schedule verification.
          </p>
        </article>
      </div>
      <section className="results-panel">
        <div className="section-kicker">
          <span>03</span>Your latest measured run
        </div>
        {!details || !features.length ? (
          <div className="empty-panel">
            <h2>No measured run yet.</h2>
            <p>
              Select learned A* below, return to the plan and click Generate.
              Your actual features, prediction, runtime and nodes will appear
              here.
            </p>
          </div>
        ) : (
          <>
            <p className="text-sm">
              {plan.resultSolver === "astar"
                ? `A* / ${cell(details.selected)}`
                : "CSP — neural values shown for reference"}{" "}
              · Model{" "}
              {details.model_available
                ? "available"
                : "unavailable; composite fallback"}
            </p>
            <div className="metric-strip">
              <div>
                <small>Raw neural prediction</small>
                <strong>{numeric(details.learned_prediction)}</strong>
                <span>remaining semesters</span>
              </div>
              <div>
                <small>Primary lower bound</small>
                <strong>{numeric(details.composite_bound)}</strong>
                <span>remaining semesters</span>
              </div>
              <div>
                <small>Solver runtime</small>
                <strong>
                  {Number.isFinite(plan.stats?.time_s)
                    ? `${(plan.stats.time_s * 1000).toFixed(2)} ms`
                    : "—"}
                </strong>
                <span>{cell(plan.stats?.nodes)} explored nodes</span>
              </div>
            </div>
            <dl className="feature-grid">
              {features.map(([name, value]) => (
                <div key={name}>
                  <dt>{name}</dt>
                  <dd>{cell(value)}</dd>
                </div>
              ))}
            </dl>
          </>
        )}
        <div className="flex flex-wrap gap-3">
          <button
            className="primary-action"
            onClick={() => onChoose("learned")}
          >
            Use learned A*
          </button>
          <button
            className="secondary-action"
            onClick={() => onChoose("composite")}
          >
            Use composite A*
          </button>
        </div>
      </section>
    </section>
  );
}
