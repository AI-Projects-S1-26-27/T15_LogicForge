const categoryKeys = {
  "Humanities Elective": "humanities",
  "Discipline Elective": "discipline",
  "Open Elective": "open",
};
export function electiveAccounting(data, plan) {
  const courses = new Map((data?.all_courses || []).map((c) => [c.code, c]));
  const minor = data?.selected_minor;
  const minorCores = [
    ...(minor?.core || []),
    ...(minor?.core_alternatives || []).map(
      (group) =>
        group.find((c) => plan.completedCourses.includes(c)) ||
        group.find((c) => plan.minorCoreChoices?.[plan.minor]?.includes(c)) ||
        group.find((c) => plan.selectedElectives.includes(c)) ||
        group.find((c) =>
          c.startsWith(
            { cse: "CS", eee: "EEE", ece: "ECE", e_and_i: "INSTR" }[
              plan.branch
            ] + " ",
          ),
        ) ||
        group[0],
    ),
  ];
  const known = [
    ...new Set([
      ...plan.completedCourses,
      ...plan.selectedElectives,
      ...Object.keys(plan.semesterAssignments || {}),
      ...minorCores,
      ...(plan.autoSelected || []),
    ]),
  ].filter((c) => courses.has(c) && !(plan.excludedCourses || []).includes(c));
  const allocations = {};
  const converted = new Set();
  if (Object.keys(plan.effectiveAllocations || {}).length) {
    Object.assign(allocations, plan.effectiveAllocations);
    for (const c of plan.convertedDelCourses || []) converted.add(c);
  } else {
    let count = 0,
      credits = 0;
    for (const code of known) {
      const c = courses.get(code);
      let allocation =
        plan.projectAllocations?.[code] ||
        plan.electiveAllocations?.[code] ||
        categoryKeys[c.category];
      if (allocation === "discipline") {
        if (count >= 4 && credits >= 12) {
          allocation = "open";
          converted.add(code);
        } else {
          count++;
          credits += c.credits;
        }
      }
      if (allocation) allocations[code] = allocation;
    }
  }
  const totals = {
    humanities: { courses: 0, credits: 0 },
    discipline: { courses: 0, credits: 0 },
    open: { courses: 0, credits: 0 },
  };
  for (const [code, allocation] of Object.entries(allocations)) {
    if (courses.has(code) && totals[allocation]) {
      totals[allocation].courses++;
      totals[allocation].credits += courses.get(code).credits;
    }
  }
  return { allocations, converted, totals };
}
