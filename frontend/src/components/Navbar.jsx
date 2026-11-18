import React, { useEffect, useState } from "react";
import { Orbit, Plus, Pencil, ArrowRight } from "lucide-react";
export default function Navbar({
  plans,
  activePlanId,
  onSelectPlan,
  onCreatePlan,
  activeTab,
  onSelectTab,
  onRename,
}) {
  const active = plans.find((p) => p.id === activePlanId) || plans[0];
  const [renaming, setRenaming] = useState(false),
    [name, setName] = useState(active.name);
  useEffect(() => {
    setName(active.name);
    setRenaming(false);
  }, [activePlanId]);
  const tabs = [
    ["plan", "Semester plan"],
    ["courses", "Choose courses"],
    ["solvers", "CSP vs A*"],
    ["heuristic", "Learned heuristic"],
    ["catalogue", "Catalogue & offerings"],
    ["compare", `Saved plans (${plans.length})`],
  ];
  return (
    <header className="masthead">
      <div className="masthead-top">
        <button
          className="brand-home"
          aria-label="Home — semester plan"
          onClick={() => onSelectTab("plan")}
        >
          <Orbit aria-hidden="true" />
          <span>
            <strong>
              GraphMind<span className="brand-dot">.</span>
            </strong>
            <small>YOUR DEGREE, WITH DIRECTION</small>
          </span>
        </button>
        <div className="plan-actions">
          <label>
            Active plan
            <select
              aria-label="Active plan"
              value={activePlanId}
              onChange={(e) => onSelectPlan(e.target.value)}
            >
              {plans.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <button
            className="rename-plan"
            aria-label="Rename plan"
            onClick={() => {
              setName(active.name);
              setRenaming(!renaming);
            }}
          >
            <Pencil aria-hidden="true" size={16} />
          </button>
          <button className="new-plan" onClick={onCreatePlan}>
            <Plus size={16} />
            New plan
          </button>
        </div>
      </div>
      {renaming && (
        <form
          className="rename-form"
          onSubmit={(e) => {
            e.preventDefault();
            onRename(activePlanId, name.trim() || "Untitled plan");
            setRenaming(false);
          }}
        >
          <label>
            Plan name
            <input
              autoFocus
              aria-label="Rename active plan"
              maxLength={80}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <button type="submit">
            Save name <ArrowRight size={14} />
          </button>
          <button type="button" onClick={() => setRenaming(false)}>
            Cancel
          </button>
        </form>
      )}
      <nav className="primary-navigation" aria-label="Planner views">
        {tabs.map(([key, title]) => (
          <button
            key={key}
            aria-current={activeTab === key ? "page" : undefined}
            onClick={() => onSelectTab(key)}
          >
            {title}
          </button>
        ))}
        <a href="/evaluation.html" className="px-3 py-2 text-sm">Volunteer evaluation</a>
      </nav>
    </header>
  );
}
