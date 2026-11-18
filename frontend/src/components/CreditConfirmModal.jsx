import React, { useEffect, useRef, useState } from "react";
export default function CreditConfirmModal({
  isOpen,
  initialCredits,
  onConfirm,
  onCancel,
}) {
  const dialog = useRef(null),
    [value, setValue] = useState(initialCredits);
  useEffect(() => {
    if (isOpen) {
      setValue(initialCredits);
      dialog.current?.showModal();
    } else dialog.current?.close();
  }, [isOpen, initialCredits]);
  return (
    <dialog
      ref={dialog}
      onCancel={(e) => {
        e.preventDefault();
        onCancel();
      }}
      className="rounded-xl border border-slate-200 p-0 w-[min(92vw,420px)] backdrop:bg-slate-900/40"
    >
      <form
        className="p-6 space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          onConfirm(Number(value));
        }}
      >
        <h2 className="font-bold text-lg">Semester credit cap</h2>
        <label className="block text-sm">
          Maximum regular-semester units
          <input
            autoFocus
            aria-label="Maximum semester credits"
            type="number"
            min={14}
            max={25}
            step={1}
            required
            value={value}
            onChange={(e) => setValue(e.target.value)}
            className="block mt-2 w-full border rounded-lg p-3"
          />
        </label>
        <p className="text-xs text-slate-500">
          The cap is a planning input. Campus registration and overload approval
          rules still apply. Summer PS-I units are handled separately.
        </p>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="border rounded-lg px-4 py-2 text-sm"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="bg-blue-600 text-white rounded-lg px-4 py-2 text-sm"
          >
            Apply credit cap
          </button>
        </div>
      </form>
    </dialog>
  );
}
