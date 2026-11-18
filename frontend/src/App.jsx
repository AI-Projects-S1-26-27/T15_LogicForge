import React, { useState, useEffect, useRef, useCallback } from "react";
import CourseSelectionTab from "./components/CourseSelectionTab.jsx";
import PageBoundary from "./components/PageBoundary.jsx";
import MoveCourseDialog from "./components/MoveCourseDialog.jsx";
import Navbar from "./components/Navbar.jsx";
import DashboardSidebar from "./components/DashboardSidebar.jsx";
import DegreeAuditCard from "./components/DegreeAuditCard.jsx";
import SemesterGrid from "./components/SemesterGrid.jsx";
import HeuristicExplainerTab from "./components/HeuristicExplainerTab.jsx";
import SolverComparisonTab, {
  planRequest,
} from "./components/SolverComparisonTab.jsx";
import ComparePlansTab from "./components/ComparePlansTab.jsx";
import CatalogueTab from "./components/CatalogueTab.jsx";
import IntroSplash from "./components/IntroSplash.jsx";
import CompletedElectivesDialog from "./components/CompletedElectivesDialog.jsx";
import CreditConfirmModal from "./components/CreditConfirmModal.jsx";

const STORAGE_KEY = "graphmind_saved_plans_v2";
const emptyResult = {
  comparisonResults: {},
  plannedSemesters: {},
  completedBySem: null,
  audit: null,
  stats: null,
  resultStatus: null,
  resultMessage: null,
  autoSelected: [],
  summerActivities: [],
  warnings: [],
  feasibility: null,
  planningFeedback: [],
  effectiveAllocations: {},
  convertedDelCourses: [],
  resultInputKey: null,
  catalogueSignature: null,
};
function freshPlan(index = 1) {
  return {
    id: crypto.randomUUID(),
    name: `Plan ${index}`,
    planningMode: "full",
    degreeType: "single",
    branch: "cse",
    currentSemester: 0,
    targetSemester: 8,
    maxCredits: 25,
    completedCourses: [],
    autoCompleteCore: true,
    selectedElectives: [],
    excludedCourses: [],
    minor: "",
    minorCoreChoices: {},
    solver: "astar",
    heuristic: "composite",
    projectRoute: "practice_school",
    autoFill: true,
    bulletinFallback: false,
    allowUnconfirmed: true,
    offeringOverrides: {},
    projectAllocations: {},
    electiveAllocations: {},
    semesterAssignments: {},
    branchProfiles: {},
    ...emptyResult,
  };
}
function removeRetiredCourse(profile) {
  if (!profile || typeof profile !== "object" || Array.isArray(profile))
    return {};
  const result = { ...profile };
  const retired = (code) =>
    typeof code === "string" &&
    code.replace(/\s+/g, "").toUpperCase() === "PHILF211";
  for (const key of [
    "completedCourses",
    "selectedElectives",
    "excludedCourses",
  ])
    if (Array.isArray(result[key]))
      result[key] = result[key].filter((c) => !retired(c));
  for (const key of [
    "offeringOverrides",
    "projectAllocations",
    "electiveAllocations",
    "semesterAssignments",
  ])
    if (
      result[key] &&
      typeof result[key] === "object" &&
      !Array.isArray(result[key])
    )
      result[key] = Object.fromEntries(
        Object.entries(result[key]).filter(([c]) => !retired(c)),
      );
  if (result.minorCoreChoices && typeof result.minorCoreChoices === "object")
    result.minorCoreChoices = Object.fromEntries(
      Object.entries(result.minorCoreChoices).map(([minor, codes]) => [
        minor,
        Array.isArray(codes) ? codes.filter((c) => !retired(c)) : [],
      ]),
    );
  if (result.branchProfiles && typeof result.branchProfiles === "object")
    result.branchProfiles = Object.fromEntries(
      Object.entries(result.branchProfiles).map(([branch, p]) => [
        branch,
        removeRetiredCourse(p),
      ]),
    );
  return result;
}
function normalize(plan, index = 1, restoreResult = true) {
  plan = removeRetiredCourse(plan);
  const base = freshPlan(index);
  const aliases = {
    "PHYS F111": "PHY F111",
    "PHYS F112": "PHY F110",
    "FIN F212": "ECON F212",
  };
  const current = plan.planningMode === "transcript" && Number.isInteger(plan.currentSemester) && plan.currentSemester>=0 && plan.currentSemester<=6 ? plan.currentSemester : 0;
  const objectValues = (value, allowed) =>
    value && typeof value === "object" && !Array.isArray(value)
      ? Object.fromEntries(
          Object.entries(value).filter(
            ([key, v]) => typeof key === "string" && allowed.includes(v),
          ),
        )
      : {};
  const normalized = {
    ...base,
    ...plan,
    id: typeof plan.id === "string" ? plan.id : base.id,
    name: typeof plan.name === "string" ? plan.name.slice(0, 80) : base.name,
    degreeType: plan.degreeType === "dual" ? "dual" : "single",
    branch: ["cse", "eee", "ece", "e_and_i"].includes(plan.branch)
      ? plan.branch
      : "cse",
    currentSemester: current,
    targetSemester:
      Number.isInteger(plan.targetSemester) &&
      [7,8].includes(plan.targetSemester)
        ? plan.targetSemester
        : 8,
    maxCredits:
      Number.isInteger(plan.maxCredits) &&
      plan.maxCredits >= 14 &&
      plan.maxCredits <= 26
        ? Math.min(plan.maxCredits, 25)
        : 22,
    solver: ["csp", "astar"].includes(plan.solver) ? plan.solver : "astar",
    heuristic: [
      "composite",
      "credit_bound",
      "critical_path",
      "learned",
    ].includes(plan.heuristic)
      ? plan.heuristic
      : "composite",
    projectRoute: [
      "",
      "thesis",
      "thesis_coursework",
      "practice_school",
    ].includes(plan.projectRoute)
      ? plan.projectRoute
      : "thesis",
    ps2Semester: [7, 8].includes(plan.ps2Semester) ? plan.ps2Semester : null,
    minor: typeof plan.minor === "string" ? plan.minor : "",
    autoFill: typeof plan.autoFill === "boolean" ? plan.autoFill : true,
    bulletinFallback: false,
    allowUnconfirmed: plan.allowUnconfirmed !== false,
    completedCourses:
      current === 0
        ? []
        : [
            ...new Set(
              (plan.completedCourses || []).map((c) => aliases[c] || c),
            ),
          ],
    autoCompleteCore: current === 0 || plan.autoCompleteCore !== false,
    selectedElectives: [...new Set(plan.selectedElectives || [])],
    excludedCourses:
      Array.isArray(plan.excludedCourses) &&
      plan.excludedCourses.every((c) => typeof c === "string")
        ? plan.excludedCourses
        : [],
    offeringOverrides: objectValues(plan.offeringOverrides, [
      "odd",
      "even",
      "both",
    ]),
    electiveAllocations: objectValues(plan.electiveAllocations, [
      "humanities",
      "discipline",
      "open",
    ]),
    semesterAssignments: Object.fromEntries(
      Object.entries(plan.semesterAssignments || {}).filter(
        ([code, term]) =>
          typeof code === "string" &&
          Number.isInteger(term) &&
          term >= 1 &&
          term <= 8,
      ),
    ),
    minorCoreChoices: Object.fromEntries(
      Object.entries(plan.minorCoreChoices || {}).filter(
        ([key, values]) =>
          typeof key === "string" &&
          Array.isArray(values) &&
          values.every((v) => typeof v === "string"),
      ),
    ),
    branchProfiles:
      plan.branchProfiles &&
      typeof plan.branchProfiles === "object" &&
      !Array.isArray(plan.branchProfiles)
        ? plan.branchProfiles
        : {},
    projectAllocations: objectValues(plan.projectAllocations, [
      "discipline",
      "open",
    ]),
  };
  const signature = JSON.stringify({
    ...planRequest(normalized),
    solver: normalized.solver,
    id: normalized.id,
  });
  const restore =
    restoreResult &&
    plan.audit?.audit_version === 4 &&
    plan.resultInputKey === signature &&
    typeof plan.catalogueSignature === "string";
  const snapshot =
    restoreResult && plan.lastGenerated
      ? normalize({ ...plan.lastGenerated, lastGenerated: null }, index, true)
      : null;
  return {
    ...normalized,
    ...(restore ? {} : emptyResult),
    lastGenerated: snapshot?.resultStatus === "PLAN" ? snapshot : null,
  };
}

function saveFile(name, body, type = "application/json") {
  const url = URL.createObjectURL(new Blob([body], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
const changeFields = new Set([
  "planningMode",
  "degreeType",
  "branch",
  "minor",
  "minorCoreChoices",
  "solver",
  "heuristic",
  "projectRoute",
  "ps2Semester",
  "autoFill",
  "bulletinFallback",
  "allowUnconfirmed",
  "offeringOverrides",
  "projectAllocations",
  "electiveAllocations",
  "semesterAssignments",
  "excludedCourses",
  "currentSemester",
  "targetSemester",
  "maxCredits",
  "completedCourses",
  "selectedElectives",
]);
export default function App() {
  const [revealPlan, setRevealPlan] = useState(0);
  const lastRevealed = useRef(0);
  const [completedPrompt, setCompletedPrompt] = useState(false);
  const [generateAfterTranscript, setGenerateAfterTranscript] = useState(false);
  const [plans, setPlans] = useState(() => {
    try {
      const data = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (
        Array.isArray(data) &&
        data.length &&
        data.every(
          (p) =>
            Array.isArray(p.completedCourses) &&
            p.completedCourses.every((c) => typeof c === "string") &&
            Array.isArray(p.selectedElectives) &&
            p.selectedElectives.every((c) => typeof c === "string"),
        )
      )
        return data.map((p, i) => normalize(p, i + 1, true));
    } catch {}
    return [freshPlan()];
  });
  const [activePlanId, setActivePlanId] = useState(() => {
      try {
        const saved = localStorage.getItem("graphmind_active_plan_id");
        if (plans.some((p) => p.id === saved)) return saved;
      } catch {}
      return plans[0].id;
    }),
    [tab, setTab] = useState("plan");
  const activePlan = plans.find((p) => p.id === activePlanId) || plans[0];
  const [curriculum, setCurriculum] = useState(null),
    [loading, setLoading] = useState(false),
    [error, setError] = useState(null),
    [storageNotice, setStorageNotice] = useState(null);
  const [coursePool, setCoursePool] = useState("humanities"),
    [moveCandidate, setMoveCandidate] = useState(null);
  const [checking, setChecking] = useState(false),
    [creditOpen, setCreditOpen] = useState(false);
  const [showIntro, setShowIntro] = useState(() => {
    try {
      return (
        !sessionStorage.getItem("graphmind_intro_seen") &&
        !matchMedia("(prefers-reduced-motion: reduce)").matches
      );
    } catch {
      return false;
    }
  });
  const finishIntro = useCallback(() => {
    try {
      sessionStorage.setItem("graphmind_intro_seen", "1");
    } catch {}
    setShowIntro(false);
  }, []);
  const inputKey = JSON.stringify({
    ...planRequest(activePlan),
    solver: activePlan.solver,
    id: activePlan.id,
  });
  const liveInput = useRef(inputKey);
  liveInput.current = inputKey;
  const generation = useRef(null),
    checkController = useRef(null),
    fileInput = useRef(null);
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(plans));
      setStorageNotice(null);
    } catch {
      setStorageNotice(
        "Browser storage is unavailable or full. Export your plans before closing this page.",
      );
    }
  }, [plans]);
  useEffect(() => {
    try {
      localStorage.setItem("graphmind_active_plan_id", activePlanId);
    } catch {}
  }, [activePlanId]);
  useEffect(() => {
    generation.current?.abort();
    checkController.current?.abort();
    setMoveCandidate(null);
    setLoading(false);
    setChecking(false);
    setError(null);
    return () => {
      generation.current?.abort();
      checkController.current?.abort();
    };
  }, [inputKey]);
  useEffect(() => {
    const c = new AbortController();
    setCurriculum(null);
    fetch(
      `/api/curriculum?branch=${encodeURIComponent(activePlan.branch)}&minor=${encodeURIComponent(activePlan.minor || "")}`,
      { signal: c.signal },
    )
      .then(async (r) => {
        const data = await r.json();
        if (!r.ok) throw Error(data.error || "Curriculum unavailable");
        if (data.app_revision !== "2026.11.18-r17")
          throw Error(
            "This dashboard is connected to an older backend. Stop the old server and start the new ZIP with python run.py --open.",
          );
        return data;
      })
      .then((data) => {
        setCurriculum(data);
        setPlans((prev) =>
          prev.map((p) =>
            p.id === activePlan.id &&
            p.audit &&
            p.catalogueSignature !== data.catalogue_signature
              ? { ...p, ...emptyResult, lastGenerated: null }
              : p,
          ),
        );
      })
      .catch((e) => {
        if (e.name !== "AbortError") setError({ message: e.message });
      });
    return () => c.abort();
  }, [activePlan.id, activePlan.branch, activePlan.minor]);
  const update = (updates) =>
    setPlans((prev) =>
      prev.map((p) =>
        p.id === activePlanId
          ? {
              ...p,
              ...(Object.keys(updates).some((k) => changeFields.has(k))
                ? emptyResult
                : {}),
              ...updates,
            }
          : p,
      ),
    );
  useEffect(() => {
    if (
      !activePlan.autoCompleteCore ||
      !curriculum ||
      curriculum.branch !== activePlan.branch
    )
      return;
    const expected =
      curriculum.reference_completed_by_semester?.[activePlan.currentSemester];
    if (!expected) return;
    setPlans((prev) =>
      prev.map((p) =>
        p.id !== activePlan.id ||
        !p.autoCompleteCore ||
        p.branch !== curriculum.branch ||
        p.currentSemester !== activePlan.currentSemester ||
        JSON.stringify([...p.completedCourses].sort()) ===
          JSON.stringify([...expected].sort())
          ? p
          : { ...p, ...emptyResult, completedCourses: [...expected] },
      ),
    );
  }, [
    curriculum,
    activePlan.id,
    activePlan.branch,
    activePlan.currentSemester,
    activePlan.autoCompleteCore,
  ]);
  useEffect(() => {
    if (activePlan.projectRoute === "practice_school" && activePlan.currentSemester >= 5 && !activePlan.completedCourses.includes("BITS F221"))
      update({ completedCourses: [...activePlan.completedCourses, "BITS F221"], autoCompleteCore: false });
  }, [activePlan.id, activePlan.projectRoute, activePlan.currentSemester, activePlan.completedCourses]);
  const toggleCompleted = (code) =>
    activePlan.currentSemester > 0 &&
    update({
      semesterAssignments: Object.fromEntries(
        Object.entries(activePlan.semesterAssignments || {}).filter(
          ([c]) => c !== code,
        ),
      ),
      autoCompleteCore: false,
      completedCourses: activePlan.completedCourses.includes(code)
        ? activePlan.completedCourses.filter((c) => c !== code)
        : [...activePlan.completedCourses, code],
    });
  const allocateElective = (code, allocation) => {
    const info = curriculum?.all_courses.find((c) => c.code === code);
    update({
      selectedElectives: [...new Set([...activePlan.selectedElectives, code])],
      excludedCourses: activePlan.excludedCourses.filter((c) => c !== code),
      electiveAllocations: {
        ...activePlan.electiveAllocations,
        [code]: allocation,
      },
      ...(info?.project_type
        ? {
            projectAllocations: {
              ...activePlan.projectAllocations,
              [code]: allocation === "discipline" ? "discipline" : "open",
            },
          }
        : {}),
    });
  };
  const removeElective = (code) => {
    const pins = { ...activePlan.semesterAssignments };
    delete pins[code];
    const allocations = { ...activePlan.electiveAllocations };
    delete allocations[code];
    const projects = { ...activePlan.projectAllocations };
    delete projects[code];
    update({
      selectedElectives: activePlan.selectedElectives.filter((c) => c !== code),
      excludedCourses: [...new Set([...activePlan.excludedCourses, code])],
      electiveAllocations: allocations,
      semesterAssignments: pins,
      projectAllocations: projects,
    });
  };
  const assignSemester = (code, semester, allocation) => {
    const pins = { ...activePlan.semesterAssignments };
    if (semester === null) {
      delete pins[code];
      update({ semesterAssignments: pins });
      return;
    }
    pins[code] = semester;
    update({
      semesterAssignments: pins,
      selectedElectives: [...new Set([...activePlan.selectedElectives, code])],
      excludedCourses: activePlan.excludedCourses.filter((c) => c !== code),
      electiveAllocations: {
        ...activePlan.electiveAllocations,
        [code]: allocation,
      },
    });
  };
  const toggleElective = (code) => {
    if (
      activePlan.selectedElectives.includes(code) ||
      activePlan.autoSelected?.includes(code)
    )
      removeElective(code);
    else {
      const course = curriculum?.all_courses.find((c) => c.code === code);
      allocateElective(
        code,
        course?.category === "Discipline Elective"
          ? "discipline"
          : course?.category === "Humanities Elective"
            ? "humanities"
            : "open",
      );
    }
  };
  const showCourses = (pool = "humanities") => {
    setCoursePool(pool);
    setTab("courses");
  };
  const minorChoice = (group, code) =>
    update({
      minorCoreChoices: {
        ...activePlan.minorCoreChoices,
        [activePlan.minor]: [
          ...(activePlan.minorCoreChoices?.[activePlan.minor] || []).filter(
            (c) => !group.includes(c),
          ),
          code,
        ],
      },
      excludedCourses: activePlan.excludedCourses.filter(
        (c) => !group.includes(c),
      ),
    });
  const openSavedPlan = (id) => {
    setPlans((prev) =>
      prev.map((p) =>
        p.id === id &&
        p.resultStatus !== "PLAN" &&
        p.lastGenerated &&
        p.lastGenerated.catalogueSignature === curriculum?.catalogue_signature
          ? {
              ...normalize(p.lastGenerated),
              id: p.id,
              name: p.name,
              lastGenerated: p.lastGenerated,
            }
          : p,
      ),
    );
    setActivePlanId(id);
    setTab("plan");
    window.scrollTo({ top: 0, behavior: "auto" });
  };
  useEffect(() => {
    if (activePlan.resultStatus !== "PLAN" || !activePlan.audit) return;
    setPlans((prev) =>
      prev.map((p) => {
        if (
          p.id !== activePlan.id ||
          (p.lastGenerated?.resultInputKey === p.resultInputKey &&
            p.lastGenerated?.plannedSemesters === p.plannedSemesters &&
            p.lastGenerated?.comparisonResults === p.comparisonResults)
        )
          return p;
        const { lastGenerated, ...snapshot } = p;
        return { ...p, lastGenerated: snapshot };
      }),
    );
  }, [
    activePlan.id,
    activePlan.resultInputKey,
    activePlan.plannedSemesters,
    activePlan.resultStatus,
    activePlan.comparisonResults,
  ]);
  const renamePlan = (id, name) =>
    setPlans((prev) =>
      prev.map((p) => (p.id === id ? { ...p, name: name.slice(0, 80) } : p)),
    );
  const changeBranch = (branch) => {
    const saved = activePlan.branchProfiles?.[branch];
    const profile = {
      completedCourses: activePlan.completedCourses,
      autoCompleteCore: activePlan.autoCompleteCore,
      selectedElectives: activePlan.selectedElectives,
      excludedCourses: activePlan.excludedCourses,
      minor: activePlan.minor,
      minorCoreChoices: activePlan.minorCoreChoices,
      electiveAllocations: activePlan.electiveAllocations,
      semesterAssignments: activePlan.semesterAssignments,
      projectAllocations: activePlan.projectAllocations,
    };
    const shared = activePlan.completedCourses.filter((code) => {
      const c = curriculum?.all_courses.find((c) => c.code === code);
      return (
        c &&
        [
          "Institutional Core",
          "General Awareness",
          "Humanities Elective",
        ].includes(c.category)
      );
    });
    const restored = saved || {
      completedCourses: shared,
      autoCompleteCore: true,
      selectedElectives: [],
      excludedCourses: [],
      minor: "",
      minorCoreChoices: {},
      electiveAllocations: {},
      semesterAssignments: {},
      projectAllocations: {},
    };
    update({
      ...restored,
      autoCompleteCore:
        activePlan.currentSemester === 0 || restored.autoCompleteCore !== false,
      completedCourses:
        activePlan.currentSemester === 0 ? [] : restored.completedCourses,
      semesterAssignments: restored.semesterAssignments || {},
      branch,
      minor:
        branch === "cse" && restored.minor === "computing_and_intelligence"
          ? ""
          : restored.minor,
      branchProfiles: {
        ...activePlan.branchProfiles,
        [activePlan.branch]: profile,
      },
    });
  };
  const applyMove = async (move) => {
    const key = inputKey,
      id = activePlan.id;
    const assignment = Object.fromEntries(
      Object.values(activePlan.plannedSemesters || {}).flatMap((t) =>
        t.courses.map((c) => [c.code, t.semester]),
      ),
    );
    const response = await fetch("/api/schedule/edit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan: planRequest(activePlan), assignment, move }),
    });
    const data = await response.json();
    if (!response.ok)
      throw {
        message: data.error || "Could not apply the move",
        issues: data.issues,
      };
    if (liveInput.current !== key)
      throw Error(
        "Plan inputs changed. Generate a fresh schedule before editing.",
      );
    setPlans((prev) =>
      prev.map((p) =>
        p.id === id
          ? {
              ...p,
              comparisonResults: {},
              resultSolver: "manual",
              resultStatus: data.status,
              resultMessage: data.message,
              stats: data.stats,
              semesterAssignments: data.request_snapshot.semester_assignments,
              resultInputKey: JSON.stringify({
                ...planRequest({
                  ...p,
                  semesterAssignments:
                    data.request_snapshot.semester_assignments,
                }),
                solver: p.solver,
                id: p.id,
              }),
              catalogueSignature: data.catalogue_signature,
              plannedSemesters: data.semesters,
              audit: data.audit,
              completedBySem: data.completed_by_sem,
              autoSelected: data.auto_selected,
              summerActivities: data.summer_activities,
              warnings: data.warnings,
              effectiveAllocations: data.effective_allocations || {},
              convertedDelCourses: data.converted_del_courses || [],
              feasibility: null,
            }
          : p,
      ),
    );
  };
  const override = (code, value) => {
    const overrides = { ...activePlan.offeringOverrides };
    if (value) overrides[code] = value;
    else delete overrides[code];
    update({ offeringOverrides: overrides });
  };
  const create = () => {
    const p = { ...freshPlan(plans.length + 1), branch: activePlan.branch };
    setPlans((prev) => [...prev, p]);
    setActivePlanId(p.id);
    setTab("plan");
  };
  const duplicate = (id) => {
    const source = plans.find((p) => p.id === id);
    const p = {
      ...source,
      ...emptyResult,
      id: crypto.randomUUID(),
      name: `${source.name} copy`.slice(0, 80),
      lastGenerated: null,
    };
    setPlans((prev) => [...prev, p]);
    setActivePlanId(p.id);
    setTab("plan");
  };
  const deletePlan = (id) => {
    if (plans.length <= 1) return;
    setPlans((prev) => prev.filter((p) => p.id !== id));
    if (id === activePlanId) setActivePlanId(plans.find((p) => p.id !== id).id);
  };
  const accept = (solver, data) => {
    update({
      solver,
      comparisonResults: activePlan.comparisonResults,
      resultInputKey: JSON.stringify({
        ...planRequest(activePlan),
        solver,
        id: activePlan.id,
      }),
      catalogueSignature: data.catalogue_signature,
      resultSolver: solver,
      resultStatus: data.status,
      resultMessage: data.message,
      stats: data.stats,
      plannedSemesters: data.semesters || {},
      completedBySem: data.completed_by_sem,
      audit: data.audit,
      autoSelected: data.auto_selected || [],
      summerActivities: data.summer_activities || [],
      warnings: data.warnings || [],
      planningFeedback: data.planning_feedback || [],
      effectiveAllocations: data.effective_allocations || {},
      convertedDelCourses: data.converted_del_courses || [],
    });
    setTab("plan");
  };
  useEffect(() => {
    if (!revealPlan || tab !== "plan" || lastRevealed.current === revealPlan)
      return;
    lastRevealed.current = revealPlan;
    const frame = requestAnimationFrame(() =>
      document
        .getElementById(
          activePlan.resultStatus === "PLAN"
            ? "generated-plan"
            : "planning-outcome",
        )
        ?.scrollIntoView({ block: "start", behavior: "auto" }),
    );
    return () => cancelAnimationFrame(frame);
  }, [revealPlan, tab, activePlan.resultStatus]);
  const generate = async () => {
    setTab("plan");
    window.scrollTo({ top: 0, behavior: "auto" });
    generation.current?.abort();
    const c = new AbortController();
    generation.current = c;
    const key = inputKey,
      id = activePlan.id;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/plan", {
        method: "POST",
        signal: c.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...planRequest(activePlan),
          solver: activePlan.solver,
          allow_solver_fallback: true,
        }),
      });
      const data = await response.json();
      if (!response.ok)
        throw { message: data.error || "Planning failed", issues: data.issues };
      if (liveInput.current !== key || c.signal.aborted) return;
      setPlans((prev) =>
        prev.map((p) =>
          p.id === id
            ? {
                ...p,
                comparisonResults: {},
                resultInputKey: key,
                catalogueSignature: data.catalogue_signature,
                resultSolver: data.solver,
                resultStatus: data.status,
                resultMessage: data.message,
                stats: data.stats,
                plannedSemesters: data.semesters || {},
                completedBySem: data.completed_by_sem,
                audit: data.audit,
                autoSelected: data.auto_selected || [],
                summerActivities: data.summer_activities || [],
                warnings: data.warnings || [],
                planningFeedback: data.planning_feedback || [],
                effectiveAllocations: data.effective_allocations || {},
                convertedDelCourses: data.converted_del_courses || [],
              }
            : p,
        ),
      );
    } catch (e) {
      if (e.name !== "AbortError" && liveInput.current === key) {
        setError(null);
        setPlans((prev) =>
          prev.map((p) =>
            p.id === id
              ? {
                  ...p,
                  ...emptyResult,
                  resultStatus: "ERROR",
                  resultMessage: e.message || "Planning request failed",
                  planningFeedback: [
                    e.message || "Network error",
                    ...(Array.isArray(e.issues)
                      ? e.issues.map((v) =>
                          typeof v === "string" ? v : JSON.stringify(v),
                        )
                      : []),
                  ],
                }
              : p,
          ),
        );
      }
    } finally {
      if (generation.current === c) {
        setLoading(false);
        if (!c.signal.aborted && liveInput.current === key) {
          setTab("plan");
          setRevealPlan((n) => n + 1);
        }
      }
    }
  };
  const feasibility = async () => {
    checkController.current?.abort();
    const c = new AbortController();
    checkController.current = c;
    const key = inputKey,
      id = activePlan.id;
    setChecking(true);
    setError(null);
    try {
      const r = await fetch("/api/feasibility", {
        method: "POST",
        signal: c.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(planRequest(activePlan)),
      });
      const d = await r.json();
      if (!r.ok) throw Error(d.error);
      if (liveInput.current === key)
        setPlans((prev) =>
          prev.map((p) => (p.id === id ? { ...p, feasibility: d } : p)),
        );
    } catch (e) {
      if (e.name !== "AbortError" && liveInput.current === key)
        setError({ message: e.message });
    } finally {
      if (checkController.current === c) setChecking(false);
    }
  };
  const importPlans = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    try {
      if (file.size > 5000000) throw Error("Plan import must be below 5 MB.");
      const parsed = JSON.parse(await file.text());
      const rows = Array.isArray(parsed) ? parsed : parsed.plans;
      if (!Array.isArray(rows) || !rows.length || rows.length > 100)
        throw Error("Choose an export containing 1–100 plans.");
      const imported = rows.map((p, i) => {
        if (
          !p ||
          !["cse", "eee", "ece", "e_and_i"].includes(p.branch) ||
          !Array.isArray(p.completedCourses) ||
          !Array.isArray(p.selectedElectives) ||
          ![...p.completedCourses, ...p.selectedElectives].every(
            (c) => typeof c === "string",
          ) ||
          !Number.isInteger(p.currentSemester) ||
          p.currentSemester < 0 ||
          p.currentSemester > 7 ||
          !Number.isInteger(p.targetSemester) ||
          p.targetSemester <= p.currentSemester ||
          p.targetSemester > 8 ||
          !Number.isInteger(p.maxCredits) ||
          p.maxCredits < 14 ||
          p.maxCredits > 25
        )
          throw Error("An imported plan has invalid settings.");
        return { ...normalize(p, i + 1, false), id: crypto.randomUUID() };
      });
      setPlans((prev) => [...prev, ...imported]);
      setActivePlanId(imported[0].id);
      setTab("plan");
    } catch (e) {
      setError({ message: e.message });
    }
  };
  const hasResult = !!(
    activePlan.audit &&
    curriculum &&
    activePlan.catalogueSignature === curriculum.catalogue_signature
  );
  const exportSchedule = () => {
    const rows = [
      ["semester", "course", "title", "units", "category", "offering_basis"],
    ];
    Object.values(activePlan.plannedSemesters).forEach((t) =>
      t.courses.forEach((c) =>
        rows.push([
          t.semester,
          c.code,
          c.title,
          c.credits,
          c.category,
          c.offering_basis,
        ]),
      ),
    );
    activePlan.summerActivities?.forEach((c) =>
      rows.push([
        `Summer after ${c.after_semester}`,
        c.code,
        c.title,
        c.credits,
        "Summer placement",
        c.source,
      ]),
    );
    saveFile(
      "graphmind-schedule.csv",
      rows
        .map((row) =>
          row
            .map((v) => '"' + String(v ?? "").replaceAll('"', '""') + '"')
            .join(","),
        )
        .join("\r\n"),
      "text/csv;charset=utf-8",
    );
  };
  useEffect(() => {
    if (generateAfterTranscript && !completedPrompt) { setGenerateAfterTranscript(false); generate(); }
  }, [generateAfterTranscript, completedPrompt]);
  return (
    <div className="app-shell">
      {showIntro && <IntroSplash onFinish={finishIntro} />}
      <Navbar
        plans={plans}
        activePlanId={activePlanId}
        onSelectPlan={openSavedPlan}
        onCreatePlan={create}
        activeTab={tab}
        onSelectTab={setTab}
        degreeType={activePlan.degreeType}
        onRename={renamePlan}
      />
      <div className="dashboard-layout">
        <DashboardSidebar
          degreeType={activePlan.degreeType}
          setDegreeType={(degreeType) => update({ degreeType })}
          branch={activePlan.branch}
          planningMode={activePlan.planningMode || "full"}
          setPlanningMode={(planningMode)=>update({planningMode,currentSemester:0,completedCourses:[],autoCompleteCore:true})}
          setBranch={changeBranch}
          minor={activePlan.minor}
          setMinor={(minor) => {
            update({ minor });
            if (minor) showCourses("minor");
          }}
          autoCompleteCore={activePlan.autoCompleteCore}
          setAutoCompleteCore={(autoCompleteCore) =>
            update({ autoCompleteCore })
          }
          currentSemester={activePlan.currentSemester}
          setCurrentSemester={(s) => {
            setCompletedPrompt(s >= 3 && s <= 6);
            update({
              currentSemester: s,
              ...(s === 0
                ? {
                    completedCourses: [],
                    autoCompleteCore: true,
                    branchProfiles: Object.fromEntries(
                      Object.entries(activePlan.branchProfiles || {}).map(
                        ([branch, profile]) => [
                          branch,
                          {
                            ...profile,
                            completedCourses: [],
                            autoCompleteCore: true,
                          },
                        ],
                      ),
                    ),
                  }
                : {}),
              targetSemester: Math.max(s + 1, activePlan.targetSemester),
            });
          }}
          targetSemester={activePlan.targetSemester}
          setTargetSemester={(targetSemester) => update({ targetSemester })}
          maxCredits={activePlan.maxCredits}
          onOpenCreditModal={() => setCreditOpen(true)}
          solver={activePlan.solver}
          setSolver={(solver) => update({ solver })}
          heuristic={activePlan.heuristic}
          setHeuristic={(heuristic) => update({ heuristic })}
          ps2Semester={activePlan.ps2Semester || ""}
          setPs2Semester={(ps2Semester) => update({ ps2Semester })}
          projectRoute={activePlan.projectRoute}
          setProjectRoute={(projectRoute) => update({ projectRoute })}
          completedCourses={activePlan.completedCourses}
          onToggleCompletedCourse={toggleCompleted}
          selectedElectives={activePlan.selectedElectives}
          onToggleElective={toggleElective}
          curriculumData={curriculum}
          onGeneratePlan={generate}
          loading={loading}
          autoFill={activePlan.autoFill}
          setAutoFill={(autoFill) => update({ autoFill })}
          allowUnconfirmed={activePlan.allowUnconfirmed}
          setAllowUnconfirmed={(allowUnconfirmed) =>
            update({ allowUnconfirmed })
          }
          bulletinFallback={activePlan.bulletinFallback}
          setBulletinFallback={(bulletinFallback) =>
            update({ bulletinFallback })
          }
          autoSelected={activePlan.autoSelected}
          excludedCourses={activePlan.excludedCourses}
          onClearExcluded={() => update({ excludedCourses: [] })}
          onCatalogue={() => setTab("catalogue")}
          onCourses={showCourses}
          onRemoveForeignTranscript={() =>
            update({
              completedCourses: activePlan.completedCourses.filter(
                (code) =>
                  !curriculum?.all_courses.find((c) => c.code === code)
                    ?.foreign_cdc,
              ),
            })
          }
          onApplyTemplate={() =>
            update({
              autoCompleteCore: true,
              completedCourses:
                curriculum.reference_completed_by_semester?.[
                  activePlan.currentSemester
                ] || [],
            })
          }
          onMinorChoice={(group, code) =>
            update({
              selectedElectives: [
                ...activePlan.selectedElectives.filter(
                  (c) => !group.includes(c),
                ),
                code,
              ],
            })
          }
          projectAllocations={activePlan.projectAllocations}
          onProjectAllocation={(code, value) =>
            update({
              projectAllocations: {
                ...activePlan.projectAllocations,
                [code]: value,
              },
            })
          }
        />
        <main id="planning-outcome" className="dashboard-main space-y-6">
          <PageBoundary
            resetKey={`${tab}:${activePlan.id}`}
            onHome={() => setTab("plan")}
          >
            {storageNotice && (
              <p role="alert" className="bg-amber-50 rounded-lg p-3 text-sm">
                {storageNotice}
              </p>
            )}
            {error && (
              <section
                role="alert"
                className="border border-red-200 bg-red-50 text-red-900 rounded-xl p-4 space-y-2"
              >
                <h2 className="font-semibold text-sm">
                  Could not generate this plan
                </h2>
                <p className="text-sm">{error.message}</p>
                {error.issues?.length > 0 && (
                  <details open>
                    <summary className="text-xs cursor-pointer">
                      Details ({error.issues.length})
                    </summary>
                    <ul className="text-xs list-disc pl-5 mt-2 space-y-1">
                      {error.issues.map((i, n) => (
                        <li key={n}>
                          {typeof i === "string"
                            ? i
                            : `${i.code}: ${i.title || ""} — ${i.reason || ""}`}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
                <button
                  onClick={() => setTab("catalogue")}
                  className="rounded-lg border bg-white px-3 py-2 text-xs"
                >
                  Review catalogue & offerings
                </button>
              </section>
            )}
            {tab === "plan" && (
              <>
                <section className="planner-hero">
                  <div>
                    <p className="eyebrow">
                      PLAN WITH PURPOSE ·{" "}
                      {activePlan.branch === "e_and_i"
                        ? "E&I"
                        : activePlan.branch.toUpperCase()}
                    </p>
                    <h1>
                      Make room for
                      <br />
                      what comes next.
                    </h1>
                    <p>
                      Your degree, electives and minor—one clear academic
                      pathway.
                    </p>
                    <button onClick={() => showCourses("discipline")}>
                      Explore your courses ↗
                    </button>
                  </div>
                  <div className="hero-orbit" aria-hidden="true">
                    <span>
                      YOUR
                      <br />
                      NEXT
                      <br />
                      CHAPTER
                    </span>
                  </div>
                </section>
                <div className="flex flex-wrap justify-between items-center gap-3">
                  <div>
                    <h1 className="text-xl font-bold">Semester plan</h1>
                    <p className="text-xs text-slate-500 mt-1">
                      {activePlan.name} · {activePlan.branch.toUpperCase()} ·{" "}
                      {activePlan.solver === "csp" ? "CSP" : "A* Search"}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      onClick={feasibility}
                      disabled={checking || loading || !curriculum}
                      className="border bg-white rounded-lg px-3 py-2 text-xs disabled:opacity-50"
                    >
                      {checking
                        ? "Checking targets…"
                        : "Compare targets 7 and 8"}
                    </button>
                    {hasResult && activePlan.audit?.verification_valid && (
                      <button
                        onClick={exportSchedule}
                        className="border bg-white rounded-lg px-3 py-2 text-xs"
                      >
                        Export schedule CSV
                      </button>
                    )}
                  </div>
                </div>
                {activePlan.branch === "cse" && activePlan.targetSemester === 7 && <section className="bg-white border rounded-xl p-5 text-sm space-y-2">
                  <h2 className="font-semibold">Seven-semester CSE planning</h2>
                  <p>From None, Practice School with PS-II in semester 7 and a 25-credit cap has a verified schedule. Full thesis has only an even-semester offering in the supplied snapshot. Completed courses, elective choices and minors can change feasibility.</p>
                  <p>Choose Practice School, PS-II semester 7, and set the cap to 25 before generating. Your selected constraints remain in effect.</p>
                </section>}
                {!hasResult && (
                  <section className="bg-white border rounded-xl p-5 space-y-3">
                    <h2 className="font-semibold">
                      Build your full degree plan
                    </h2>
                    <ol className="list-decimal pl-5 text-sm text-slate-600 space-y-2">
                      <li>
                        Choose your branch and target finish: semester 7 or 8.
                      </li>
                      <li>
                        Choose your route, optional minor and required
                        electives. Auto-fill can recommend the remaining
                        electives.
                      </li>
                      <li>
                        Review odd/even offering evidence, then generate a
                        schedule.
                      </li>
                    </ol>
                    <p className="text-xs text-slate-500">
                      Changing inputs clears previous results. Automatic core
                      completion follows your selected branch and last finished
                      semester. Turn it off for a custom transcript.
                    </p>
                  </section>
                )}
                {activePlan.resultMessage && (
                  <p
                    role="status"
                    className="bg-blue-50 rounded-lg p-4 text-sm text-blue-900"
                  >
                    {activePlan.resultStatus}: {activePlan.resultMessage}
                  </p>
                )}
                {loading && (
                  <p role="status" className="pool-note">
                    Generating and independently checking your schedule…
                  </p>
                )}
                {activePlan.planningFeedback?.length > 0 &&
                  activePlan.resultStatus !== "PLAN" && (
                    <section role="alert" className="edit-error">
                      <h2>No verified schedule for these settings</h2>
                      <ul>
                        {activePlan.planningFeedback.map((reason, i) => (
                          <li key={i}>{reason}</li>
                        ))}
                      </ul>
                      {activePlan.targetSemester < 8 && (
                        <button
                          className="secondary-action"
                          onClick={() => update({ targetSemester: 8 })}
                        >
                          Change target to semester 8
                        </button>
                      )}
                    </section>
                  )}
                {activePlan.feasibility && (
                  <section className="border bg-white rounded-xl p-4 space-y-3">
                    <h2 className="font-semibold text-sm">
                      Tested graduation targets
                    </h2>
                    <div className="grid sm:grid-cols-3 gap-3">
                      {activePlan.feasibility.results.map((r) => (
                        <div
                          key={r.target}
                          className="bg-slate-50 rounded-lg p-3 text-xs"
                        >
                          <strong>Semester {r.target}</strong>
                          <p className="mt-1">
                            {r.verified && r.requirements_met
                              ? "Verified coursework plan"
                              : r.status}
                          </p>
                          <p className="mt-1 text-slate-600">{r.message}</p>
                        </div>
                      ))}
                    </div>
                    <p className="text-xs text-slate-500">
                      {activePlan.feasibility.note}
                    </p>
                  </section>
                )}
                <DegreeAuditCard audit={hasResult ? activePlan.audit : null} />
                {hasResult && (
                  <>
                    <details className="border rounded-xl bg-white p-4 text-xs">
                      <summary className="font-semibold cursor-pointer">
                        Recommendations & planning notes
                      </summary>
                      <p className="mt-2">
                        Auto-selected electives:{" "}
                        {activePlan.autoSelected.length
                          ? activePlan.autoSelected.join(", ")
                          : "none"}
                        .
                      </p>
                      <p className="mt-2">
                        Uncheck a suggested course in the sidebar to exclude it
                        and generate an alternative recommendation.
                      </p>
                      {activePlan.warnings.map((w, i) => (
                        <p key={i} className="mt-2 text-slate-600">
                          {w}
                        </p>
                      ))}
                    </details>
                    {activePlan.summerActivities?.map((c) => (
                      <p
                        key={c.code}
                        className="bg-amber-50 rounded-lg p-3 text-sm"
                      >
                        <strong>
                          Summer after semester {c.after_semester}:
                        </strong>{" "}
                        {c.code} · {c.title} · {c.credits} units, outside the
                        regular-semester cap.
                      </p>
                    ))}
                    {activePlan.resultStatus === "PLAN" && (
                      <SemesterGrid
                        solver={activePlan.resultSolver}
                        minorName={curriculum?.selected_minor?.name}
                        onMoveCourse={(course, term) =>
                          setMoveCandidate({ course, term })
                        }
                        editingDisabled={loading || checking}
                        hasVerifiedPlan={activePlan.audit.verification_valid}
                        currentSemester={activePlan.currentSemester}
                        targetSemester={activePlan.targetSemester}
                        completedBySem={activePlan.completedBySem}
                        plannedSemesters={activePlan.plannedSemesters}
                      />
                    )}
                  </>
                )}
              </>
            )}
            {tab === "courses" && (
              <CourseSelectionTab
                key={`${coursePool}:${activePlan.branch}:${activePlan.minor}`}
                initialPool={coursePool}
                data={curriculum}
                plan={activePlan}
                onHome={() => setTab("plan")}
                onSelect={allocateElective}
                onExclude={removeElective}
                onAllocation={allocateElective}
                onMinorChoice={minorChoice}
                onSemesterChoice={assignSemester}
              />
            )}
            {tab === "solvers" && (
              <SolverComparisonTab
                plan={activePlan}
                onUseResult={accept}
                onComparison={(comparisonResults) =>
                  update({ comparisonResults })
                }
              />
            )}
            {tab === "heuristic" && (
              <HeuristicExplainerTab
                plan={activePlan}
                onHome={() => setTab("plan")}
                onChoose={(heuristic) => {
                  update({ solver: "astar", heuristic });
                  setTab("plan");
                }}
              />
            )}
            {tab === "catalogue" && (
              <CatalogueTab
                data={curriculum}
                plan={activePlan}
                onOverride={override}
                onToggleCompleted={toggleCompleted}
              />
            )}
            {tab === "compare" && (
              <>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() =>
                      saveFile(
                        "graphmind-plans.json",
                        JSON.stringify({ schema_version: 1, plans }, null, 2),
                      )
                    }
                    className="border bg-white rounded-lg px-3 py-2 text-sm"
                  >
                    Export plans JSON
                  </button>
                  <button
                    onClick={() => fileInput.current?.click()}
                    className="border bg-white rounded-lg px-3 py-2 text-sm"
                  >
                    Import plans JSON
                  </button>
                  <input
                    ref={fileInput}
                    type="file"
                    accept=".json,application/json"
                    className="hidden"
                    onChange={importPlans}
                  />
                </div>
                <ComparePlansTab
                  plans={plans}
                  activePlanId={activePlanId}
                  onSelectPlan={openSavedPlan}
                  onDeletePlan={deletePlan}
                  onDuplicate={duplicate}
                  onRename={(id, name) =>
                    setPlans((prev) =>
                      prev.map((p) =>
                        p.id === id ? { ...p, name: name.slice(0, 80) } : p,
                      ),
                    )
                  }
                />
              </>
            )}
          </PageBoundary>
        </main>
      </div>
      <MoveCourseDialog
        course={moveCandidate?.course}
        sourceSemester={moveCandidate?.term}
        plan={activePlan}
        onApply={applyMove}
        onClose={() => setMoveCandidate(null)}
      />
      <CreditConfirmModal
        isOpen={creditOpen}
        initialCredits={activePlan.maxCredits}
        onConfirm={(maxCredits) => {
          update({ maxCredits });
          setCreditOpen(false);
        }}
        onCancel={() => setCreditOpen(false)}
      />
    </div>
  );
}
