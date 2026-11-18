import TranscriptPanel from "./TranscriptPanel.jsx";
import React, { useState } from "react";
export default function DashboardSidebar(p) {
  const [showTranscript, setShowTranscript] = useState(false),
    [query, setQuery] = useState(""),
    [all, setAll] = useState(false),
    [includeElectives, setIncludeElectives] = useState(true),
    [passedCategory, setPassedCategory] = useState("all");
  const field = "settings-field";
  const data = p.curriculumData,
    minor = data?.selected_minor,
    core = data?.degree_core_summary;
  const foreignTranscript = p.completedCourses.filter(
    (code) => data?.all_courses.find((c) => c.code === code)?.foreign_cdc,
  );
  const transcript = new Map(
    (data?.all_courses || [])
      .filter(
        (c) =>
          (passedCategory === "all" || c.category === passedCategory) && (includeElectives ||
          [
            "Institutional Core",
            "Discipline Core",
            "General Awareness",
          ].includes(c.category)),
      )
      .map((c) => [c.code, c]),
  );
  p.completedCourses.forEach((c) => {
    if (!transcript.has(c))
      transcript.set(
        c,
        data?.all_courses.find((info) => info.code === c) || {
          code: c,
          title: "Legacy transcript entry · review scope",
        },
      );
  });
  return (
    <aside className="dashboard-sidebar">
      <section className="settings-panel">
        <div className="section-kicker">
          <span>01</span>Plan settings
        </div>
        <label className={field}>Planning mode<select aria-label="Planning mode" value={p.planningMode || "full"} onChange={e=>p.setPlanningMode(e.target.value)}><option value="full">Full degree · start semester 1</option><option value="transcript">Remaining degree · use my transcript</option></select></label>
        <label className={field}>
          Discipline branch
          <select
            aria-label="Discipline branch"
            value={p.branch}
            onChange={(e) => p.setBranch(e.target.value)}
          >
            <option value="cse">Computer Science · CSE</option>
            <option value="e_and_i">Electronics & Instrumentation · E&I</option>
            <option value="ece">Electronics & Communication · ECE</option>
            <option value="eee">Electrical & Electronics · EEE</option>
          </select>
        </label>
        {core && (
          <p className="core-requirement">
            Degree CDCs:{" "}
            <strong>
              {core.course_count} courses ·{" "}
              {core.credits_min === core.credits_max
                ? core.credits_min
                : `${core.credits_min}–${core.credits_max}`}{" "}
              units
            </strong>
          </p>
        )}
        <div className="settings-pair">
          <label className={field}>
            Target finish
            <select
              aria-label="Target finish"
              value={p.targetSemester}
              onChange={(e) => p.setTargetSemester(Number(e.target.value))}
            >
              {[7,8].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
        </div>
        <div className="credit-setting">
          <span>
            Credit cap <strong>{p.maxCredits}/semester</strong>
          </span>
          <button onClick={p.onOpenCreditModal}>Change</button>
        </div>
        <label className={field}>
          Planning algorithm
          <select
            aria-label="Planning algorithm"
            value={p.solver}
            onChange={(e) => p.setSolver(e.target.value)}
          >
            <option value="astar">A* Search</option>
            <option value="csp">CSP · constraint search</option>
          </select>
        </label>
        {p.solver === "astar" && (
          <label className={field}>
            A* heuristic
            <select
              aria-label="A* heuristic"
              value={p.heuristic}
              onChange={(e) => p.setHeuristic(e.target.value)}
            >
              <option value="composite">Composite lower bound</option>
              <option value="credit_bound">Credit lower bound</option>
              <option value="learned">Learned-guided A*</option>
            </select>
          </label>
        )}
        <label className={field}>
          Thesis / Practice School route
          <select
            aria-label="Project route"
            value={p.projectRoute || ""}
            onChange={(e) => p.setProjectRoute(e.target.value)}
          >
            <option value="">Choose a route</option>
            <option value="thesis">Full thesis · 16 units</option>
            <option value="thesis_coursework">
              Thesis 9 + 6–9 elective units
            </option>
            <option value="practice_school">
              Practice School I + II · 25 units
            </option>
          </select>
        </label>
        {p.projectRoute === "practice_school" && (
          <label className={field}>
            PS-II placement
            <select
              aria-label="PS-II semester"
              value={p.ps2Semester}
              onChange={(e) =>
                p.setPs2Semester(e.target.value ? Number(e.target.value) : null)
              }
            >
              <option value="">Automatic · semester 7 or 8</option>
              {[7, 8].map((term) => (
                <option
                  key={term}
                  value={term}
                  disabled={
                    term <= p.currentSemester || term > p.targetSemester
                  }
                >
                  Semester {term}
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="settings-check">
          <input
            type="checkbox"
            checked={p.autoFill}
            onChange={(e) => p.setAutoFill(e.target.checked)}
          />
          <span>Auto-fill remaining elective requirements</span>
        </label>
        <label className="settings-check">
          <input
            type="checkbox"
            checked={p.allowUnconfirmed}
            onChange={(e) => p.setAllowUnconfirmed(e.target.checked)}
          />
          <span>
            Allow unlisted courses in either semester (planning assumption)
          </span>
        </label>
        {p.allowUnconfirmed && (
          <p className="settings-help">
            Unlisted courses will not block generation. Their semester
            availability is assumed, not confirmed by the PDFs.
          </p>
        )}
        <button
          className="primary-action generate-action"
          onClick={p.onGeneratePlan}
          disabled={p.loading || !data}
        >
          {p.loading
            ? "Building your pathway…"
            : `Generate plan (${p.solver === "astar" ? "A*" : "CSP"})`}
        </button>
      </section>
      {p.planningMode === "transcript" && <TranscriptPanel {...p} />}
      <section className="settings-panel">
        <div className="section-kicker">
          <span>03</span>Elective choices
        </div>
        <p className="settings-help">
          {p.selectedElectives.length} required selections ·{" "}
          {p.autoSelected?.length || 0} suggestions. Complete pools open on the
          main page without inner scrollbars.
        </p>
        <div className="elective-launchers">
          {[
            ["humanities", "HuEl", data?.humanities_electives?.length],
            ["discipline", "DEL", data?.discipline_electives?.length],
            ["open", "OpEl", data?.open_electives?.length],
          ].map(([key, title, count]) => (
            <button key={key} onClick={() => p.onCourses(key)}>
              {title}
              <span>{count || 0}</span>
            </button>
          ))}
        </div>
        {p.excludedCourses?.length > 0 && (
          <button className="text-action" onClick={p.onClearExcluded}>
            Clear {p.excludedCourses.length} exclusions
          </button>
        )}
        <button className="text-action" onClick={() => p.onCourses("projects")}>
          Elective project courses →
        </button>
      </section>
      <section className="settings-panel minor-settings">
        <div className="section-kicker">
          <span>04</span>Optional minor
        </div>
        <label className={field}>
          Choose your minor
          <select
            id="minor"
            value={p.minor || ""}
            onChange={(e) => p.setMinor(e.target.value)}
          >
            <option value="">No minor</option>
            {data?.minors?.map((m) => (
              <option
                key={m.id}
                value={m.id}
                disabled={m.excluded_branches.includes(p.branch)}
              >
                {m.name}
                {m.excluded_branches.includes(p.branch)
                  ? " (non-CSE only)"
                  : ""}
              </option>
            ))}
          </select>
        </label>
        {minor && (
          <>
            <h3>{minor.name}</h3>
            <p className="core-requirement">
              <strong>
                {minor.required_core_courses} required CDCs ·{" "}
                {minor.required_core_credits_min} units
              </strong>
              <br />
              {minor.minimum_courses} courses / {minor.minimum_credits} units
              overall.
            </p>
            <p className="settings-help">
              Core courses are included and scheduled automatically. Choose
              elective preferences or let auto-fill complete the remaining
              requirements.
            </p>
            <button
              className="secondary-action"
              onClick={() => p.onCourses("minor")}
            >
              View minor CDCs & electives →
            </button>
          </>
        )}
      </section>
    </aside>
  );
}
