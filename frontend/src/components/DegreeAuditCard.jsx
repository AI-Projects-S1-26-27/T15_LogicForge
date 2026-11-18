import React from "react";
export default function DegreeAuditCard({ audit }) {
  if (!audit) return null;
  const pct = Math.min(
    100,
    Math.round(
      (100 * audit.total_credits_planned) / audit.total_credits_required,
    ),
  );
  return (
    <section className="bg-white border rounded-xl p-5 space-y-4 mb-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-base font-bold">
          Graduation feasibility · target semester {audit.target_semester}
        </h2>
        <span
          className={`rounded-full px-3 py-1 text-xs font-medium ${audit.verification_valid ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"}`}
        >
          {audit.verification_valid
            ? "Schedule independently verified"
            : "No verified schedule"}
        </span>
      </div>
      <p
        className={`text-sm font-semibold ${audit.is_eligible_for_graduation ? "text-emerald-700" : "text-amber-800"}`}
      >
        {audit.graduation_assessment}
      </p>
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
        {[
          ["Completed credits", audit.completed_credits],
          ["Planned credits", audit.planned_credits],
          [
            "Total / minimum",
            `${audit.total_credits_planned} / ${audit.total_credits_required}`,
          ],
          ["Coursework courses", `${audit.coursework_count} / 41`],
        ].map(([name, value]) => (
          <div key={name} className="rounded-lg bg-slate-50 p-3">
            <p className="text-xs text-slate-500">{name}</p>
            <p className="text-lg font-bold mt-1">{value}</p>
          </div>
        ))}
      </div>
      <div
        role="progressbar"
        aria-label="Total credit progress"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={pct}
        className="bg-slate-100 rounded-full h-2"
      >
        <div
          className="bg-blue-600 h-2 rounded-full"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="text-sm bg-slate-50 rounded-lg p-3 space-y-1">
        <p>
          Remaining capacity:{" "}
          <strong>{audit.remaining_credit_capacity} credits</strong> · minimum
          credits still required:{" "}
          <strong>{audit.remaining_credits_required}</strong>
        </p>
        <p
          className={
            audit.capacity_possible ? "text-slate-600" : "text-red-700"
          }
        >
          {audit.capacity_possible
            ? "The credit capacity test passes; prerequisites, category requirements and the project route still need to pass."
            : "The target is impossible under the current credit cap, even before prerequisite restrictions."}
        </p>
        <p className="text-xs text-slate-500">
          Credit-only earliest bound: semester {audit.earliest_credit_bound}.
          This is a lower bound, not a promised graduation date.
        </p>
      </div>
      {audit.categories && (
        <div className="grid sm:grid-cols-3 gap-3">
          {Object.entries(audit.categories).map(([name, c]) => (
            <div key={name} className="bg-slate-50 rounded-lg p-3 text-xs">
              <p className="font-medium">{name}</p>
              <p className="mt-1">
                {c.credits} / {c.credit_minimum} units · {c.courses} /{" "}
                {c.course_minimum} courses
              </p>
            </div>
          ))}
        </div>
      )}
      {audit.minor && (
        <div className="border rounded-lg p-3 text-xs space-y-2">
          <strong>
            Minor in {audit.minor.name}:{" "}
            {audit.minor.coursework_met
              ? "coursework requirements met"
              : "requirements pending"}
          </strong>
          <p>
            {audit.minor.count} courses · {audit.minor.credits} units ·
            mandatory-major overlap:{" "}
            {audit.minor.major_overlap.join(", ") || "none"}
          </p>
          <p>{audit.minor.certificate_status}</p>
        </div>
      )}
      {audit.offering_assumptions?.length > 0 && (
        <details className="bg-amber-50 rounded-lg p-3 text-xs">
          <summary className="cursor-pointer font-semibold">
            Explicit offering assumptions ({audit.offering_assumptions.length})
          </summary>
          {audit.offering_assumptions.map((c) => (
            <p key={c.code} className="mt-2">
              {c.code}: {c.terms.join(" + ")} · {c.basis}
            </p>
          ))}
        </details>
      )}
      {audit.blockers?.length > 0 && (
        <details open>
          <summary className="font-semibold text-sm cursor-pointer">
            Remaining requirements ({audit.blockers.length})
          </summary>
          <ul className="list-disc pl-5 mt-2 space-y-1 text-xs text-amber-900">
            {audit.blockers.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
        </details>
      )}
      <p className="text-xs text-slate-500">{audit.audit_source}</p>
    </section>
  );
}
