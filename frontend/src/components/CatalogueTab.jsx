import React, { useState } from "react";
export const offeringLabel = (c, allowUnconfirmed = false) =>
  ({
    odd: "Odd only",
    even: "Even only",
    both: "Odd + even",
    unconfirmed: allowUnconfirmed ? "Assumed odd + even" : "Unconfirmed",
  })[c.offering_status] || "Unconfirmed";
export function formulaText(f) {
  if (!f) return "No prerequisite rule supplied";
  if (f.kind === "leaf")
    return f.course + (f.relation === "CO" ? " (co-requisite)" : "");
  return (
    "(" +
    (f.items || []).map(formulaText).join(f.kind === "or" ? " OR " : " AND ") +
    ")"
  );
}
export default function CatalogueTab({
  data,
  plan,
  onOverride,
  onToggleCompleted,
}) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [category, setCategory] = useState("all");
  const [active, setActive] = useState(null);
  const courses = (data?.all_courses || []).filter(
    (c) =>
      `${c.code} ${c.title}`.toLowerCase().includes(query.toLowerCase()) &&
      (status === "all" || c.offering_status === status) &&
      (category === "all" || c.category === category),
  );
  return (
    <section className="space-y-5">
      <div className="bg-white border rounded-xl p-5 space-y-3">
        <h1 className="text-xl font-bold">
          Course catalogue & semester offerings
        </h1>
        <p className="text-sm text-slate-600">
          Only the courses in your supplied images are selectable. Odd/even
          labels come from exact course codes in the teaching timetable, not
          from the bulletin’s recommended year.
        </p>
        <div className="grid sm:grid-cols-2 gap-3 text-xs">
          <div className="bg-slate-50 rounded-lg p-3">
            <strong>Odd snapshot · Hyderabad</strong>
            <p className="mt-1">
              {data?.sources?.odd?.snapshot || "2026–27 Semester I"}
            </p>
          </div>
          <div className="bg-slate-50 rounded-lg p-3">
            <strong>Even snapshot · Hyderabad</strong>
            <p className="mt-1">
              {data?.sources?.even?.snapshot || "2024–25 Semester II"}
            </p>
          </div>
        </div>
        <p className="text-xs text-amber-900">
          These snapshots are from different academic years. Repeating their
          parity into future years is a planning projection. F-series courses
          absent from both can be scheduled in either semester when planning
          assumptions are enabled. These are not confirmed offerings. U-series
          courses are not silently substituted.
        </p>
        <div className="flex flex-wrap gap-2 text-xs">
          {Object.entries(data?.availability_counts || {}).map(
            ([key, value]) => (
              <span key={key} className="rounded bg-slate-100 px-2 py-1">
                {key}: {value}
              </span>
            ),
          )}
        </div>
      </div>
      <details className="bg-white border rounded-xl p-5">
        <summary className="font-semibold cursor-pointer">
          Semester-wise programme structure · {plan.branch.toUpperCase()}
        </summary>
        <p className="text-xs text-slate-500 my-3">
          Reference pattern transcribed from your images. Actual odd/even
          offering observations are listed separately below. Cores may move when
          offerings and prerequisites allow; these elective slot ranges are
          reference pacing, not additional graduation requirements.
        </p>
        <div className="grid sm:grid-cols-2 gap-4">
          {Array.from({ length: 8 }, (_, i) => i + 1).map((term) => (
            <div key={term} className="bg-slate-50 rounded-lg p-3 text-xs">
              <h3 className="font-semibold mb-2">Semester {term}</h3>
              {(data?.patterns?.[term] || []).map((c) => (
                <p key={c.code} className="mt-1">
                  <strong>{c.code}</strong> · {c.title} · {c.credits} units
                </p>
              ))}
              {(data?.elective_pattern?.[term] || []).map((slot) => (
                <p key={slot} className="mt-2 text-blue-800">
                  {slot}
                </p>
              ))}
              {term === 5 && plan.branch === "eee" && (
                <p className="mt-2 text-amber-900">
                  Choose MATH F212 (3 units) OR ME F344 (2 units), not both.
                </p>
              )}
              {term === 4 && (
                <p className="mt-2 text-amber-900">
                  PS option: a separate PS-I summer placement follows this year.
                </p>
              )}
            </div>
          ))}
        </div>
      </details>
      <div className="bg-white border rounded-xl p-4 space-y-4">
        <div className="flex flex-wrap gap-3">
          <label className="text-xs flex-1 min-w-[160px]">
            Find a course
            <input
              aria-label="Search catalogue"
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="block mt-1 w-full rounded-lg border p-2 text-sm"
            />
          </label>
          <label className="text-xs">
            Observed offering
            <select
              aria-label="Filter offering"
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="block mt-1 border rounded-lg p-2 text-sm"
            >
              {["all", "odd", "even", "both", "unconfirmed"].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <label className="text-xs">
            Degree category
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="block mt-1 border rounded-lg p-2 text-sm"
            >
              {[
                "all",
                ...new Set((data?.all_courses || []).map((c) => c.category)),
              ].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
        </div>
        <p className="text-xs text-slate-500">
          {courses.length} matching courses. Individual offering confirmations
          are saved in this plan.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-slate-50">
              <tr>
                {[
                  "Course",
                  "Units",
                  "Observed / reference",
                  "Passed",
                  "Offering confirmation",
                ].map((h) => (
                  <th key={h} className="p-3 font-semibold">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {courses.map((c) => (
                <tr key={c.code} className="border-t align-top">
                  <td className="p-3 min-w-[160px]">
                    <button
                      onClick={() =>
                        setActive(active === c.code ? null : c.code)
                      }
                      className="font-semibold text-blue-700 underline underline-offset-2"
                    >
                      {c.code}
                    </button>
                    <p className="text-xs mt-1">{c.title}</p>
                    <p className="text-xs text-slate-500 mt-1">{c.category}</p>
                    {c.project_type && plan.projectAllocations?.[c.code] && (
                      <p className="text-xs text-blue-800 mt-1">
                        Plan allocation: {plan.projectAllocations[c.code]}{" "}
                        elective
                      </p>
                    )}
                    {active === c.code && (
                      <div className="mt-3 text-xs space-y-2">
                        <p>
                          <strong>Prerequisites:</strong>{" "}
                          {formulaText(c.formula)}
                        </p>
                        {c.external_prerequisites?.length > 0 && (
                          <p className="text-amber-900">
                            Outside this catalogue:{" "}
                            {c.external_prerequisites.join(", ")}. These are not
                            assumed completed.
                          </p>
                        )}
                        {Object.entries(c.offering_evidence || {}).map(
                          ([term, e]) => (
                            <p key={term}>
                              <strong>
                                {term}, PDF page {e.page}:
                              </strong>{" "}
                              {e.excerpt}
                            </p>
                          ),
                        )}
                        {!c.offered_terms.length && (
                          <p>
                            No teaching-row evidence in either uploaded
                            timetable.
                          </p>
                        )}
                        {c.data_note && <p>{c.data_note}</p>}
                      </div>
                    )}
                  </td>
                  <td className="p-3">{c.credits}</td>
                  <td className="p-3 min-w-[120px]">
                    <span
                      className={`text-xs ${c.offering_status === "unconfirmed" ? "text-amber-800" : "text-slate-700"}`}
                    >
                      {offeringLabel(c, plan.allowUnconfirmed)}
                    </span>
                    {c.recommended_semester && (
                      <p className="text-xs text-slate-500 mt-1">
                        Pattern: semester {c.recommended_semester}
                      </p>
                    )}
                  </td>
                  <td className="p-3">
                    <input
                      aria-label={`Mark ${c.code} completed`}
                      disabled={plan.currentSemester === 0}
                      title={
                        plan.currentSemester === 0
                          ? "Full-degree planning starts from semester 1"
                          : undefined
                      }
                      type="checkbox"
                      checked={plan.completedCourses.includes(c.code)}
                      onChange={() => onToggleCompleted(c.code)}
                    />
                  </td>
                  <td className="p-3">
                    <select
                      aria-label={`Confirm offering ${c.code}`}
                      value={plan.offeringOverrides?.[c.code] || ""}
                      onChange={(e) => onOverride(c.code, e.target.value)}
                      className="border rounded-lg p-2 text-xs"
                    >
                      <option value="">Use source evidence</option>
                      <option value="odd">Confirmed odd</option>
                      <option value="even">Confirmed even</option>
                      <option value="both">Confirmed both</option>
                    </select>
                    {plan.offeringOverrides?.[c.code] && (
                      <p className="text-xs text-amber-900 mt-1">
                        User confirmation overrides the uploaded evidence.
                      </p>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!courses.length && (
          <p className="text-sm text-slate-500">
            No courses match these filters.
          </p>
        )}
      </div>
    </section>
  );
}
