import React, { useState } from "react";
export default function SemesterGrid({
  solver = "astar",
  hasVerifiedPlan = false,
  currentSemester,
  targetSemester,
  completedBySem,
  plannedSemesters,
  onMoveCourse,
  minorName,
  editingDisabled = false,
}) {
  const [showHistory, setShowHistory] = useState(false);
  const terms = [
    ...Array.from(
      { length: targetSemester - currentSemester },
      (_, i) => currentSemester + i + 1,
    ),
    ...(showHistory
      ? Array.from({ length: currentSemester }, (_, i) => i + 1)
      : []),
  ];
  const other = Object.values(completedBySem || {}).flatMap(
    (t) => t.unassigned_courses || [],
  );
  return (
    <section id="generated-plan" className="semester-pathway">
      <div className="pathway-heading">
        <div>
          <p className="eyebrow">Your academic pathway</p>
          <h2>A semester at a time.</h2>
          <p>
            Past courses use reference semesters. Future courses follow the
            selected offerings and prerequisites.
          </p>
        </div>
        {hasVerifiedPlan && (
          <span className="verified-tag">
            {solver === "manual"
              ? "Edited & reverified"
              : `Verified ${solver === "astar" ? "A*" : "CSP"} schedule`}
          </span>
        )}
      </div>
      {other.length > 0 && (
        <details className="unassigned-history">
          <summary>
            Other passed courses · semester not recorded ({other.length})
          </summary>
          <div>
            {other.map((c) => (
              <p key={c.code}>
                <strong>{c.code}</strong> · {c.title} · {c.credits} units
              </p>
            ))}
          </div>
        </details>
      )}
      {currentSemester > 0 && (
        <button
          className="secondary-action"
          onClick={() => setShowHistory(!showHistory)}
        >
          {showHistory
            ? "Hide completed semesters"
            : "Show completed semesters"}
        </button>
      )}
      <div className="semester-grid">
        {terms.map((term) => {
          const past = term <= currentSemester,
            data = past ? completedBySem?.[term] : plannedSemesters?.[term],
            courses = data?.courses || [];
          return (
            <article
              key={term}
              className={`semester-card ${past ? "is-past" : "is-future"}`}
            >
              <header>
                <div>
                  <small>
                    {past
                      ? "COMPLETED / REFERENCE"
                      : solver === "manual"
                        ? "MANUALLY ADJUSTED"
                        : "PLANNED PATHWAY"}
                  </small>
                  <h3>Semester {term}</h3>
                </div>
                <span>
                  {data?.credits || 0}
                  <small>units</small>
                </span>
              </header>
              {!past && (
                <p className="semester-status">
                  {hasVerifiedPlan
                    ? solver === "manual"
                      ? "Edited · reverified"
                      : `Planned (${solver === "astar" ? "A*" : "CSP"})`
                    : "Not scheduled"}
                </p>
              )}
              <div className="semester-courses">
                {courses.map((c) => (
                  <div key={c.code} className="scheduled-course">
                    <div className="scheduled-course-top">
                      <strong>{c.code}</strong>
                      <span>{c.credits} units</span>
                    </div>
                    <p>{c.title}</p>
                    <div className="scheduled-badges">
                      <span
                        className={`category-${c.category?.includes("Humanities") ? "humanities" : c.category?.includes("Discipline Elective") ? "del" : c.category?.includes("Open") ? "open" : "core"}`}
                      >
                        {c.category}
                      </span>
                      {c.converted_to_open && (
                        <span className="minor-course-badge">
                          Extra DEL → OpEl
                        </span>
                      )}
                      {c.assigned_semester && (
                        <span className="minor-course-badge">
                          Fixed semester {c.assigned_semester}
                        </span>
                      )}
                      {c.minor_role && (
                        <span className="minor-course-badge">
                          {c.minor_role === "Minor Core"
                            ? "Minor CDC"
                            : "Minor elective"}
                          {minorName ? ` · ${minorName}` : ""}
                        </span>
                      )}
                    </div>
                    {!past && hasVerifiedPlan && (
                      <div className="scheduled-course-footer">
                        <small>
                          {c.offered_terms?.join(" + ") || c.offering_basis}
                        </small>
                        <button
                          aria-label={`Move ${c.code}`}
                          disabled={editingDisabled}
                          onClick={() => onMoveCourse?.(c, term)}
                        >
                          Move / swap ↗
                        </button>
                      </div>
                    )}
                    {c.placement_reasons?.length > 0 && <details className="text-xs mt-2"><summary className="cursor-pointer">Why this placement?</summary><ul className="list-disc pl-4">{c.placement_reasons.map((reason,i)=><li key={i}>{typeof reason === "string" ? reason : JSON.stringify(reason)}</li>)}</ul></details>}
                  </div>
                ))}
                {!courses.length && (
                  <p className="empty-semester">
                    {past
                      ? "No passed courses recorded for this reference semester."
                      : "No courses required here; the verified plan places them in other semesters."}
                  </p>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
