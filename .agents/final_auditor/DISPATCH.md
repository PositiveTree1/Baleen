# Dispatch: Final Forensic Integrity Auditor

Your Working Directory: `c:\Users\arthu\Documents\Baleen-master\.agents\final_auditor`
Your Request File: `c:\Users\arthu\Documents\Baleen-master\.agents\ORIGINAL_REQUEST.md`
Your Project File: `c:\Users\arthu\Documents\Baleen-master\.agents\PROJECT.md`
Your Test Ready File: `c:\Users\arthu\Documents\Baleen-master\.agents\TEST_READY.md`

Tasks:
1. Conduct an exhaustive project-wide forensic integrity audit of the entire Baleen codebase, all modifications made across Milestones M-A1, M-A2, M-A3, M-B1, M-B2, and M-B3.
2. Run the complete backend test suite:
   `& "backend/.venv/Scripts/python.exe" -m pytest backend/tests/ -v`
3. Verify:
   - All 348 tests execute and pass 100%.
   - All 220 scenarios in `backend/tests/scenarios/` execute genuine mathematical calculations and invariant assertions.
   - Zero hardcoding of test outputs, zero facade/dummy implementations, and zero test bypasses.
   - Invariants (Cash non-negativity, margin equality, HWM monotonicity, FIFO lot split fee/dollar conservation, 2026 Polymarket fee curves, zero orphaned lots, ghost sell prevention, IEEE numerical safety) are strictly enforced and verified.
4. Record your final forensic audit report and verdict (CLEAN / INTEGRITY VIOLATION) in `c:\Users\arthu\Documents\Baleen-master\.agents\final_auditor\handoff.md` and send a message to parent when complete.
