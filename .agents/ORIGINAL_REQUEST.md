# Original User Request

## 2026-08-29T10:56:20Z

Deploy a team of agents to perform a comprehensive code audit of the entire Baleen codebase (`c:\Users\arthu\Documents\Baleen-master`). The team will analyze all source code across backend Python, listener TypeScript, and frontend Next.js modules, with priority focus on paper trading realism, execution fill simulation, dynamic fees, slippage modeling, and mathematical logic, alongside full code coverage for bugs and edge cases.

Working directory: c:\Users\arthu\Documents\Baleen-master
Integrity mode: development

## Requirements

### R1. Comprehensive Full-Codebase Audit
Examine all components of the Baleen system:
- Backend services, endpoints, and background workers (`backend/app/`)
- Ingestion listener, Envio HyperSync stream parsing, block checkpointing, and forwarding (`listener/src/`)
- Frontend application, trade drawer, state display, and probability calculations (`frontend/`)
- Database interactions, query efficiency, transaction boundaries, and schemas (`db/` and `backend/app/database.py`)

Identify all logic bugs, runtime exceptions, concurrency/race condition hazards, unhandled error states, and numerical edge cases.

### R2. Paper Trading Simulation, Fill Logic & Uneven Edge Audit
Prioritize deep inspection of paper trading simulation mechanics to detect any artificial advantages, ungrounded assumptions, or execution divergences from real Polymarket trading:
- Fill model and order book walking: check for synthetic/stale midpoints, zero-slippage assumptions, or fills against non-existent liquidity.
- Dynamic quadratic taker fee calculation: verify against 2026 Polymarket fee curve specifications across all asset categories.
- Latency and timestamp modeling: check for lookahead bias, unaligned tick timestamps, or instant fills that ignore real block settlement.
- Filter and rebate mechanics: verify Maker rebate micro-trader filtering and binary outcome probability inversions (`1 - p` for Token 1).
- PnL and equity curve calculations: audit peak-to-trough drawdown formulas, mark-to-market valuations, and cash balance accounting.

### R3. Mathematical & Quantitative Integrity
Verify statistical and scoring calculations throughout the system:
- Wilson score lower bounds, win rate filtering, and whale cohort inclusion criteria.
- Kelly criterion dynamic position sizing and portfolio weight balancing.
- Multi-candidate / multi-outcome price discovery calibrations.

### R4. Structured Audit Report & Remediation Recommendations
Deliver a comprehensive audit document containing:
- Findings categorized by severity: Critical (loss of funds/simulation breakdown), High (incorrect PnL/math), Medium (concurrency/stale data), Low/Info (code quality/minor edge cases).
- Precise file path and line number ranges for every finding (`file:///...#Lxx-Lyy`).
- Detailed explanation of failure mechanics and potential uneven paper trading edges.
- Concrete code remediation diffs/patches for each issue.
- A dedicated "Ambiguities & Anomalies" section highlighting any unintuitive code patterns or design decisions requiring user clarification.

## Acceptance Criteria

### Audit Coverage & Depth
- [ ] 100% of source files in `backend/app`, `listener/src`, `db`, and core `frontend` pages/components are inspected.
- [ ] Existing test suites (`pytest` in backend, `jest` in listener) are executed and evaluated against the codebase.
- [ ] Every identified issue includes exact file and line references (`file:///...#Lxx-Lyy`).
- [ ] The report contains a dedicated section specifically detailing Paper Trading Realism and any potential unfair edges.
- [ ] Concrete diffs/patches are provided for confirmed bugs.
- [ ] Any ambiguous logic or architectural anomalies are flagged in a user review queue with specific questions.
