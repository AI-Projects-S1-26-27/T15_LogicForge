import React, { useState } from "react";
import { electiveAccounting } from "../lib/electiveAccounting.js";
import { offeringLabel, formulaText } from "./CatalogueTab.jsx";
const poolNames = {
  humanities: "HuEl",
  discipline: "DEL",
  open: "OpEl",
  minor: "Minor",
  projects: "Projects",
};
export default function CourseSelectionTab({
  data,
  plan,
  initialPool = "humanities",
  onSelect,
  onExclude,
  onMinorChoice,
  onAllocation,
  onHome,
  onSemesterChoice,
}) {
  const [pool, setPool] = useState(initialPool),
    [search, setSearch] = useState("");
  const minor = data?.selected_minor;
  const accounting = electiveAccounting(data, plan);
  const lists = {
    humanities: data?.humanities_electives || [],
    discipline: data?.discipline_electives || [],
    open: data?.open_electives || [],
    minor: minor?.courses || [],
    projects: data?.project_courses || [],
  };
  const all = lists[pool].filter((c) =>
    `${c.code} ${c.title}`.toLowerCase().includes(search.toLowerCase()),
  );
  const checked = (code) =>
    plan.selectedElectives.includes(code) || plan.autoSelected?.includes(code);
  return (
    <section className="space-y-6">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Build your curriculum</p>
          <h1>Choose your courses.</h1>
          <p>
            Complete branch-specific pools from your images. Lists expand on the
            page without inner scrollbars.
          </p>
        </div>
        <button className="secondary-action" onClick={onHome}>
          Back to semester plan
        </button>
      </div>
      <div
        className="course-pool-tabs"
        role="tablist"
        aria-label="Course pools"
      >
        {Object.entries(poolNames).map(([key, title]) => (
          <button
            role="tab"
            aria-selected={pool === key}
            key={key}
            onClick={() => {
              setPool(key);
              setSearch("");
            }}
          >
            {title}
            <span>{lists[key].length}</span>
          </button>
        ))}
      </div>
      <div className="selection-toolbar">
        <label>
          Search this pool
          <input
            type="search"
            aria-label="Search elective pool"
            placeholder="Course code or title"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <div>
          <strong>{plan.selectedElectives.length}</strong> explicit selections ·{" "}
          <strong>{plan.autoSelected?.length || 0}</strong> suggestions
          <p>
            Each course counts once. Extra DELs count as OpEls after 4 DEL
            courses and 12 DEL credits. These are minimum requirements, not
            selection caps.
          </p>
        </div>
      </div>
      <div className="metric-strip">
        {[
          ["humanities", "HuEl", 3, 9],
          ["discipline", "DEL", 4, 12],
          ["open", "OpEl", 5, 15],
        ].map(([key, label, count, units]) => (
          <div key={key}>
            <small>{label} minimum</small>
            <strong>
              {accounting.totals[key].credits} / {units} credits
            </strong>
            <span>
              {accounting.totals[key].courses} / {count} courses
            </span>
          </div>
        ))}
      </div>
      {pool === "minor" && !minor && (
        <div className="empty-panel">
          <h2>Select an optional minor first</h2>
          <p>
            Choose a minor in Plan settings. Its required CDCs, units and
            complete elective pool will appear here.
          </p>
        </div>
      )}
      {pool === "minor" && minor && (
        <div className="minor-overview">
          <div>
            <p className="eyebrow">Minor in {minor.name}</p>
            <h2>
              {minor.required_core_courses} required CDCs ·{" "}
              {minor.required_core_credits_min ===
              minor.required_core_credits_max
                ? minor.required_core_credits_min
                : `${minor.required_core_credits_min}–${minor.required_core_credits_max}`}{" "}
              units
            </h2>
            <p>
              At least {minor.minimum_electives_needed} elective courses /{" "}
              {minor.minimum_elective_credits_needed} elective units;{" "}
              {minor.minimum_courses} courses / {minor.minimum_credits} units
              overall.
            </p>
            <p>
              Core courses are included automatically and scheduled with your
              degree courses. At most two mandatory-major courses / six units
              can overlap.
            </p>
          </div>
          {minor.core_alternatives.map((group, i) => (
            <label key={i}>
              Core alternative
              <select
                value={
                  group.find((c) => plan.completedCourses.includes(c)) ||
                  group.find((c) =>
                    plan.minorCoreChoices?.[plan.minor]?.includes(c),
                  ) ||
                  group.find((c) => plan.selectedElectives.includes(c)) ||
                  group.find((c) =>
                    c.startsWith(
                      { cse: "CS", eee: "EEE", ece: "ECE", e_and_i: "INSTR" }[
                        plan.branch
                      ] + " ",
                    ),
                  ) ||
                  group[0]
                }
                onChange={(e) => onMinorChoice(group, e.target.value)}
              >
                {group.map((code) => (
                  <option key={code}>{code}</option>
                ))}
              </select>
            </label>
          ))}
        </div>
      )}
      {pool === "open" && (
        <p className="pool-note">
          OpEl includes all eligible courses from the supplied images, including
          humanities and approved DEL courses when allocated as open electives.
          Another programme’s CDC is available only when you deliberately select
          it; it is not auto-added.
        </p>
      )}
      {pool === "projects" && (
        <p className="pool-note">
          Maximum three DEL projects, three open projects and five overall. DEL
          limits: study 1, laboratory 2, design 2, special 1. Outside-branch
          projects require open allocation unless an allied-branch approval is
          supplied.
        </p>
      )}
      <div className="course-selection-grid">
        {all.map((c) => {
          const alternative = minor?.core_alternatives.find((g) =>
            g.includes(c.code),
          );
          const chosenAlternative =
            alternative &&
            (alternative.find((code) => plan.completedCourses.includes(code)) ||
              alternative.find((code) =>
                plan.minorCoreChoices?.[plan.minor]?.includes(code),
              ) ||
              alternative.find((code) =>
                plan.selectedElectives.includes(code),
              ) ||
              alternative.find((code) =>
                code.startsWith(
                  { cse: "CS", eee: "EEE", ece: "ECE", e_and_i: "INSTR" }[
                    plan.branch
                  ] + " ",
                ),
              ) ||
              alternative[0]);
          const core =
            pool === "minor" &&
            (minor.core.includes(c.code) || chosenAlternative === c.code);
          const degreeCategory = c.degree_category || c.category;
          const mandatory = [
            "Discipline Core",
            "Institutional Core",
            "University Core (First Year)",
            "General Awareness",
          ].includes(degreeCategory);
          const selected = checked(c.code),
            passed = plan.completedCourses.includes(c.code);
          const allocation =
            accounting.allocations[c.code] ||
            plan.electiveAllocations?.[c.code] ||
            (c.project_type && plan.projectAllocations?.[c.code]) ||
            (degreeCategory === "Humanities Elective"
              ? "humanities"
              : degreeCategory === "Discipline Elective"
                ? "discipline"
                : "open");
          const inferred =
            pool === "minor" || pool === "projects"
              ? degreeCategory === "Discipline Elective"
                ? "discipline"
                : degreeCategory === "Humanities Elective"
                  ? "humanities"
                  : "open"
              : pool;
          return (
            <article
              key={c.code}
              className={`course-option ${selected ? "is-chosen" : ""} ${core ? "is-core" : ""}`}
            >
              <div className="course-option-top">
                <span>{c.code}</span>
                <strong>{c.credits} units</strong>
              </div>
              <h3>{c.title}</h3>
              <div className="course-tags">
                <span>{offeringLabel(c, plan.allowUnconfirmed)}</span>
                {core && <span>Required minor CDC</span>}
                {accounting.converted.has(c.code) && (
                  <span>Extra DEL → OpEl</span>
                )}
                {c.manual_open_only && !core && (
                  <span>Other programme CDC · manual only</span>
                )}
                {c.recommended_semester && (
                  <span>Pattern sem {c.recommended_semester}</span>
                )}
              </div>
              <details>
                <summary>Prerequisites & source</summary>
                <p>{formulaText(c.formula)}</p>
                {c.prerequisite_normalizations?.map((n, i) => (
                  <p key={i}>
                    {n.from} → {n.to}: {n.basis}
                  </p>
                ))}
                {Object.entries(c.offering_evidence || {}).map(([term, e]) => (
                  <p key={term}>
                    {term} · PDF page {e.page}
                  </p>
                ))}
              </details>
              <div className="course-option-actions">
                {core ? (
                  <span className="core-included">Included automatically</span>
                ) : alternative ? (
                  <button
                    className="secondary-action"
                    onClick={() => onMinorChoice(alternative, c.code)}
                  >
                    Choose this alternative
                  </button>
                ) : mandatory ? (
                  <span className="core-included">
                    Already required by degree
                  </span>
                ) : passed ? (
                  <span className="core-included">Already passed</span>
                ) : (
                  <button
                    aria-label={`${selected ? "Remove" : "Add"} ${c.code} as ${poolNames[inferred] || inferred}`}
                    onClick={() =>
                      selected ? onExclude(c.code) : onSelect(c.code, inferred)
                    }
                    className={selected ? "secondary-action" : "primary-action"}
                  >
                    {selected ? "Remove from selection" : "Add to plan"}
                  </button>
                )}
                {selected && (
                  <span className="allocation-label">
                    Counts as {poolNames[allocation] || allocation}
                  </span>
                )}
              </div>
              {!passed && !mandatory && !alternative && (
                <label className="semester-placement">
                  Schedule in semester
                  <select
                    aria-label={`Semester for ${c.code}`}
                    value={plan.semesterAssignments?.[c.code] || ""}
                    onChange={(e) =>
                      onSemesterChoice(
                        c.code,
                        e.target.value ? Number(e.target.value) : null,
                        selected ? allocation : inferred,
                      )
                    }
                  >
                    <option value="">Automatic — planner chooses</option>
                    {plan.semesterAssignments?.[c.code] &&
                      (plan.semesterAssignments[c.code] <=
                        plan.currentSemester ||
                        plan.semesterAssignments[c.code] >
                          plan.targetSemester) && (
                        <option value={plan.semesterAssignments[c.code]}>
                          Outside current horizon: semester{" "}
                          {plan.semesterAssignments[c.code]}
                        </option>
                      )}
                    {Array.from(
                      { length: plan.targetSemester - plan.currentSemester },
                      (_, i) => plan.currentSemester + i + 1,
                    ).map((term) => {
                      const override = plan.offeringOverrides?.[c.code];
                      const terms = override
                        ? override === "both"
                          ? ["odd", "even"]
                          : [override]
                        : c.offered_terms?.length
                          ? c.offered_terms
                          : plan.allowUnconfirmed
                            ? ["odd", "even"]
                            : [];
                      const allowed = terms.includes(term % 2 ? "odd" : "even");
                      return (
                        <option key={term} value={term} disabled={!allowed}>
                          Semester {term}
                          {allowed ? "" : " — not offered"}
                        </option>
                      );
                    })}
                  </select>
                  <small>
                    Choosing a semester adds this course and fixes its
                    placement. Prerequisites and credit limits still apply.
                  </small>
                </label>
              )}
              {selected &&
                !core &&
                !passed &&
                !accounting.converted.has(c.code) &&
                pool !== allocation &&
                ["humanities", "discipline", "open"].includes(pool) && (
                  <button
                    className="text-action"
                    onClick={() => onAllocation(c.code, pool)}
                  >
                    Count as {poolNames[pool]} instead
                  </button>
                )}
            </article>
          );
        })}
      </div>
      {!all.length && !(pool === "minor" && !minor) && (
        <div className="empty-panel">No courses match this search.</div>
      )}
    </section>
  );
}
