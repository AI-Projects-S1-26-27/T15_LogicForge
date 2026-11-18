import React, { useEffect, useRef, useState } from "react";
export default function MoveCourseDialog({
  course,
  sourceSemester,
  plan,
  onApply,
  onClose,
}) {
  const dialog = useRef(null),
    [target, setTarget] = useState(""),
    [swap, setSwap] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(null);
  useEffect(() => {
    if (course) {
      setTarget("");
      setSwap("");
      setError(null);
      dialog.current?.showModal();
    } else dialog.current?.close();
  }, [course]);
  const candidates = plan?.plannedSemesters?.[target]?.courses || [];
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onApply({
        course: course.code,
        target_semester: Number(target),
        swap_with: swap || null,
      });
      onClose();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };
  return (
    <dialog
      ref={dialog}
      className="move-dialog"
      onCancel={(e) => {
        if (busy) e.preventDefault();
        else onClose();
      }}
    >
      <form onSubmit={submit}>
        <p className="eyebrow">Fine-tune your pathway</p>
        <h2>Move {course?.code}</h2>
        <p>
          {course?.title} · currently semester {sourceSemester}
        </p>
        <label>
          Move to semester
          <select
            required
            aria-label="Move to semester"
            value={target}
            onChange={(e) => {
              setTarget(e.target.value);
              setSwap("");
            }}
          >
            <option value="">Choose a semester</option>
            {Array.from(
              {
                length:
                  (plan?.targetSemester || 8) - (plan?.currentSemester || 0),
              },
              (_, i) => (plan?.currentSemester || 0) + i + 1,
            )
              .filter((s) => s !== sourceSemester)
              .map((s) => (
                <option key={s}>{s}</option>
              ))}
          </select>
        </label>
        <label>
          Optional swap with a course in that semester
          <select
            aria-label="Swap with course"
            value={swap}
            onChange={(e) => setSwap(e.target.value)}
          >
            <option value="">Move without swapping</option>
            {candidates.map((c) => (
              <option key={c.code} value={c.code}>
                {c.code} · {c.title}
              </option>
            ))}
          </select>
        </label>
        <p className="settings-help">
          The backend rechecks the whole schedule, including prerequisites,
          offerings, caps and the final project. An invalid change leaves your
          current schedule untouched.
        </p>
        {error && (
          <div role="alert" className="edit-error">
            <strong>{error.message}</strong>
            <ul>
              {error.issues?.map((v, i) => (
                <li key={i}>{typeof v === "string" ? v : JSON.stringify(v)}</li>
              ))}
            </ul>
          </div>
        )}
        <div className="dialog-actions">
          <button
            className="secondary-action"
            disabled={busy}
            type="button"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            className="primary-action"
            disabled={busy || !target}
            type="submit"
          >
            {busy ? "Validating…" : "Validate & apply move"}
          </button>
        </div>
      </form>
    </dialog>
  );
}
