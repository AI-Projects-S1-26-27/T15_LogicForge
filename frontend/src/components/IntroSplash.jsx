import React, { useEffect, useState } from "react";
import { Orbit } from "lucide-react";

export default function IntroSplash({ onFinish }) {
  const finishRef = React.useRef(onFinish);
  finishRef.current = onFinish;
  const [phase, setPhase] = useState("traversing"); // 'traversing' -> 'gliding' -> 'done'
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    // Step-by-step traversal along the graph path
    const t1 = setTimeout(() => setActiveStep(1), 300);
    const t2 = setTimeout(() => setActiveStep(2), 650);
    const t3 = setTimeout(() => setActiveStep(3), 1000);
    const t4 = setTimeout(() => setActiveStep(4), 1350);
    const t5 = setTimeout(() => setActiveStep(5), 1700);

    // Trigger glide to top-left
    const tGlide = setTimeout(() => {
      setPhase("gliding");
    }, 2000);

    // Complete transition and unmount splash
    const tDone = setTimeout(() => {
      setPhase("done");
      finishRef.current?.();
    }, 2800);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      clearTimeout(t4);
      clearTimeout(t5);
      clearTimeout(tGlide);
      clearTimeout(tDone);
    };
  }, []);

  if (phase === "done") return null;

  const isGliding = phase === "gliding";

  return (
    <div
      className={`fixed inset-0 z-50 transition-all duration-700 ease-in-out ${
        isGliding ? "bg-transparent" : "bg-white/95 backdrop-blur-md"
      }`}
    >
      <button
        type="button"
        onClick={() => finishRef.current?.()}
        className="absolute right-4 top-4 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700"
      >
        Skip intro
      </button>
      <div
        className={`absolute transition-all duration-700 ease-in-out flex flex-col sm:flex-row items-center gap-4 ${
          isGliding
            ? "top-3 left-6 sm:left-8 scale-[0.62] origin-top-left"
            : "top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 scale-100"
        }`}
      >
        {/* GraphMind Orbit Brand Logo */}
        <div className="relative w-24 h-24 sm:w-28 sm:h-28 shrink-0 flex items-center justify-center rounded-2xl bg-gradient-to-br from-slate-900 to-slate-800 p-4 shadow-xl border border-slate-700">
          <Orbit
            className={`w-14 h-14 sm:w-16 sm:h-16 text-[#ffb69c] transition-all duration-700 ${
              activeStep >= 5 ? "scale-110 rotate-180" : "scale-100"
            }`}
            strokeWidth={1.8}
            aria-hidden="true"
          />
        </div>

        {/* Brand Text Header */}
        <div className="flex flex-col">
          <div className="flex items-center gap-2.5">
            <h1 className="text-3xl sm:text-4xl font-serif text-slate-900 tracking-tight">
              GraphMind<span className="text-[#ffb69c]">.</span>
            </h1>
            <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 border border-blue-200">
              AI Planner
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-600 font-medium tracking-widest uppercase mt-0.5">
            Your degree, with direction
          </p>

          {!isGliding && (
            <div className="mt-2.5 flex items-center gap-2 text-xs font-semibold text-blue-700 animate-pulse">
              <span className="inline-block w-2 h-2 rounded-full bg-blue-600 animate-ping" />
              {activeStep < 5 ? "Preparing your planner…" : "Workspace ready"}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
