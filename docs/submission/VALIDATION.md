# r17 validation

## Release r17 — proposal implementation and evaluation

- Restored completed-transcript planning as an optional Remaining degree mode; full-degree mode remains default with targets7/8 and cap25.
- Added live forward-chaining potential-reachability checks and completed category accumulation, placement derivations on course cards, and budgeted minimal-conflict analysis with honest timeout/minimality flags.
- Generated3000 exact optimal-length small synthetic states by complete shorter-horizon CSP proofs and independent SAT verification. Trained portable6→16→8→1 MLP on held-out synthetic-family split; production remains composite-primary neural tie-breaking. Direct neural guidance is evaluated only as a research variant.
- Executed E1–E4 on200 synthetic profiles:164 solver-ready,36 preparation-blocked. CSP returned88 plans and A*87; all returned plans verified. Raw statuses, search effort, ablations, bootstrap CIs, paired Wilcoxon and stratum statistics included. Bounded A* failure is not an infeasibility proof.
- Executed500 exact-optimality comparisons on100 heldout small instances and20 brute-force minimal-core checks. All500 solutions verified and had observed gap0; this is finite evidence, not a universal optimality claim.
- 379 automated tests passed. Browser validated transcript entry, remaining plan, reload, placement explanations and evaluation page.
- Prepared /evaluation.html with anonymous volunteer tasks, local feedback download and analysis script. E5 is pending6–10 actual volunteers. Inherited unverified E5 claims are preserved separately and excluded from current evidence. No report or PPT was created.


See experiments/proposal/README.md for reproduction commands and evaluation/completion_status.json for the explicit completion boundary.
