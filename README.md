# Invoice Processing and Reconciliation Toolkit 🔧📄

A compact, modular Python toolkit for ingesting, matching, validating, and reporting on invoice documents against purchase order (PO) data. The project was designed as an educational / prototype codebase with clear separation of concerns: extraction, matching, validation, decision reasoning, and reporting. It is suitable as a starting point for building automated invoice reconciliation workflows and experimenting with agent-based pipelines.

---

## Table of Contents

- [Key Features](#key-features)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Install](#install)
  - [Quick Start](#quick-start)
- [Running Tests](#running-tests)
- [Design & Architecture](#design--architecture)
  - [Agents](#agents)
  - [Core Components](#core-components)
  - [Data model](#data-model)
- [How to extend](#how-to-extend)
- [Troubleshooting & Notes](#troubleshooting--notes)
- [Contributing](#contributing)
- [License](#license)

---

## Key Features ✅

- Modular agent-based pipeline that separates responsibilities: extraction, matching, validation, and reporting.
- Decision confidence calculations that combine extraction and matching results with penalty factors from validation agents.
- Simple HTML reporting utility for human-readable results.
- Lightweight test runner to run a small set of behavior-focused tests without pytest dependency.

---

## Repository Structure 🗂️

Top-level layout (important files/folders):

- `process_invoice.py` — CLI helper to run invoice processing (sample entry point).
- `requirements.txt` — Python dependencies.
- `agents/` — Agent implementations: orchestration, extraction, matching, validation, reporting, and shared agent state/messages.
- `core/` — Core utilities and configuration (e.g. thresholds).
- `data/` — Example data used by tests and examples (PO database, example extracted invoices).
- `tests/` — Small test suite and runner (`tests/run_tests.py`) that does not require pytest.
- `docs/` — Markdown docs, example invoices, rules and notes.

Each agent is intentionally small and focused to make it straightforward to replace or extend individual behavior.

---

## Getting Started 🚀

### Prerequisites

- Python 3.10 or newer (the project is compatible with 3.10+)
- Recommended: virtual environment for dependency isolation

### Install

1. Create and activate a virtual environment (optional but recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install required packages:

```bash
pip install -r requirements.txt
```

> Note: The project uses standard libraries wherever practical. See `requirements.txt` for any optional or third-party libraries.

### Quick Start

Process a sample extracted invoice via the provided entry point:

```bash
python process_invoice.py data/mock_extraction/invoice_5_extracted.json
```

This will run the orchestration pipeline using the sample PO database under `data/database/purchase_orders.json` and print a short summary. Use the `--report` flag to generate an HTML report output.

---

## Running Tests ✅

A minimal, dependency-free test runner is provided at `tests/run_tests.py`. It imports `tests/test_confidence.py` as a module and executes the defined test functions.

Run the tests with:

```bash
python3 tests/run_tests.py
```

What the test runner does and why it’s lightweight:
- It adds the repository root to `sys.path` so imports like `agents.*` work reliably regardless of current working directory.
- Tests use repository relative paths to load sample data from `data/`.
- Designed for fast feedback without requiring pytest; you can switch to `pytest` later for richer reporting.

If all is well you should see:

```
Running test: test_overlap_penalty_and_message... OK
Running test: test_decision_confidence_math... OK
All tests passed.
```

---

## Design & Architecture 🧭

This section gives a concise explanation of the main components and how they interact.

### Agents

Agents implement small, composable behaviors and communicate via recorded `AgentMessage` objects. Primary agents include:

- **Orchestrator** (`agents/orchestrator.py`): Central pipeline runner that invokes extraction, matching, validation and collates results into a single `processing_results` dict.
- **ExtractionAgent**: Responsible for parsing or accepting pre-extracted invoice payloads. In this codebase examples are pre-extracted JSON documents.
- **MatchingAgent** (`matching.py`): Matches invoice references and line items to a PO database, producing an overlap metric and `po_match_confidence`.
- **ValidationAgent** (`validation.py`): Applies reconciliation rules (e.g., price variance thresholds). It uses constants defined in `core/config.py` (`PRICE_FLAG_LOW_PERCENT`, `PRICE_FLAG_HIGH_PERCENT`) and returns penalty factors and human-readable messages.
- **Reporting** (`reporting.py`): Produces HTML summaries and other human-facing artifacts.

Agents update a shared `AgentState` and append `AgentMessage` objects describing decisions and recommended actions.

### Core Components

- `core/config.py` — Central constants and thresholds used by validation logic. Adjust here to change behavior globally.
- `agents/agent_state.py` — Tracks agent invocations and stored messages.
- `agents/base_agent.py` — Base class for common agent behavior.

### Data model

- Purchase Orders (PO) — stored as JSON under `data/database/purchase_orders.json`. The test helper reads the `purchase_orders` key or the entire file if it is an array.
- Extracted invoices — JSON files in `data/mock_extraction/` representing already-extracted invoice fields (line items, unit prices, invoice metadata).

Key fields the pipeline uses:
- `line_items`: list of {description, quantity, unit_price, line_total}
- `po_reference`: a reference string parsed from the invoice (if present)

---

## How to Extend 🛠️

- Replace or extend `MatchingAgent` to support new fuzzy matching heuristics (e.g., embedding-based similarity).
- Plug in a real extraction component that turns PDFs into the expected JSON extraction format; keep the rest of the pipeline unchanged.
- Add more validation rules in `ValidationAgent` or split them into separate small-check agents for better isolation.
- Add more tests under `tests/` and consider adopting `pytest` for fixtures and test parametrization.

---

## Troubleshooting & Notes ⚠️

- If imports fail when running tests, ensure you run `python3 tests/run_tests.py` from the repository root. The test runner already inserts the repository root to `sys.path` to prevent this issue when run from other locations.
- If you adjust config thresholds in `core/config.py`, unit test expectations might need updates.
- For reproducible builds and CI, lock the environment or pin versions in `requirements.txt`.

---

## Contributing 🤝

Contributions are welcome. Please:

1. Open an issue to discuss significant changes or proposals.
2. Fork the repository and make a branch for your change.
3. Add tests for new behavior and run `python3 tests/run_tests.py`.
4. Submit a pull request with a clear description of the change.

---

## License 📄

This project is provided under an MIT-style license unless otherwise specified. See the `LICENSE` file for full details.

---

If you'd like, I can also:
- Add a small CONTRIBUTING.md with PR guidelines and a checklist. 💡
- Add a `Makefile` or GitHub Actions workflow to automate tests and linting. 🔧

If you want any of those, tell me which one to add and I will implement it.