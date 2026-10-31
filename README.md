# SQL Query Repair

An original `nanoagent.plugin/v0001` task plugin for COMP 480/580, based on the supplied **NanoAgent production** plugin template and informed by the TA's **Weather Alert** plugin's pinned-reference + deterministic-verifier pattern. This is an independent repository: it does not import the other four tasks.

**Purpose.** Correct a defective SQL query so that it produces the intended aggregated results on three distinct SQLite databases.

**Supported task input:** `{"case":"region-revenue","seed":7}`. Supported datasets: `region-revenue` and `overdue-count` with integer seed 1–10000.

## Tools

| Contract tool | What it does | Input/output |
|---|---|---|
| `pin_sql_truth` | Execute the known-correct query against the same three fixtures before the agent starts; pin fixture rows and reference results. | `contract.py` typed input and reference output |
| `read_sql_case` | Read the relational schema, business requirement, faulty SQL and multi-fixture evaluation rules. | Typed task input and read output |
| `run_candidate_sql` | Execute a candidate read-only SELECT against three deterministic SQLite fixtures and save its executed rows, column names and SQL to `reports/result.json`. | Typed candidate input and save output |

**Task:** `repair-sql` (`runner: agent`). NanoAgent invokes the reference tool *before* the agent starts and does not expose its result to the agent. The agent can call `read_sql_case` and `run_candidate_sql` and must finish with `submit` using the save tool's returned object. It cannot use the reference tool. The `submit` tool is supplied by NanoAgent and must **not** appear in `contract.TOOLS`.

All tools use MCP over stdio and `NANOAGENT_WORKSPACE` supplied by NanoAgent. MCP tool schemas come from `slimconfig.output_schema()` of the classes in `contract.py`. Exceptions become tool errors, not successful results. The task has **no network access and requires no task-specific API key**.

## Layout

```text
.
├── nanoagent.yaml          # v0001 manifest: id, runtime, tools, task, permissions
├── contract.py             # typed input/output data classes; declarations only
├── .env                    # only comments/required environment-variable NAMES, never secrets
├── pyproject.toml          # independent uv project, Python 3.12+
├── uv.lock                 # pinned from supplied TA reference dependency graph
├── README.md / LICENSE / .gitignore
├── src/plugin/
│   ├── __main__.py         # MCP stdio server
│   ├── logic.py            # tools, reference and candidate creation
│   ├── datasets.py         # deterministic built-in task fixtures
│   └── storage.py          # bounded actual JSON report writer
├── verifier/
│   ├── __init__.py         # verify_input/output/task entry points
│   ├── rules.py            # independent deterministic outcome checks
│   └── checks.py           # safe saved-file, SHA-256 and verdict checks
├── tests/
│   ├── test_verifier.py    # positive, negative, missing, malformed, boundary cases
│   └── inputs/sample.json # sample task arguments
├── product/                # marketplace metadata and original SVG icon
└── ui/                     # default NanoAgent v0001 schema renderer
```

**How verification works.** Independently derives the exact expected aggregates from pinned source records using pure Python (not SQLite or an LLM), confirms the reference is consistent, then compares the saved executed column names and row multisets on all three fixtures. Rejects missing/malformed/tampered reports and wrong SQL results. The verifier imports only pure allowed Python modules, reads only the workspace report, never calls an LLM, and returns a `valid`, `score`, `message`, `details` verdict. The task score is 1.0 for a valid result, 0.0 otherwise.

## Develop and run

### Prerequisites

- Python **3.12 or newer**, Git, and [uv](https://docs.astral.sh/uv/getting-started/installation/). If you're on Windows, the course requires **WSL** for the RUSH Lab installer.
- Obtain the course [NanoAgent](https://github.com/RUSH-LAB/nanoagent) repository; its **production** snapshot is the basis of this plugin, using `spec: nanoagent.plugin/v0001`.
- Network access when installing dependencies. `uv` retrieves `slimconfig` from its upstream Git repository (declared in `[tool.uv.sources]`). This is a dependency fetch, **not** an API called by the task.

### Local setup and automated tests

From this plugin's folder:

```bash
uv sync --extra dev --frozen
uv run --extra dev --frozen pytest -v
```

The tests directly call the real tool implementation and the deterministic verifier, including tests that intentionally provide wrong results and alter/remove the saved file. No LLM or external API is required for tests. The test input file is `tests/inputs/sample.json`; edit it to choose other supported datasets.

### Inspect the plugin with NanoAgent

Install NanoAgent's development dependencies in its own project (the supplied `nanoagent-production/nanoagent` folder), then **from this plugin's folder**, use the NanoAgent executable from that project:

```bash
# One-time, from /path/to/nanoagent-production/nanoagent:
uv sync

# Back in THIS plugin folder:
uv run --project /path/to/nanoagent-production/nanoagent nanoagent plugin inspect .
```

If your nanoagent project checkout does not expose a `nanoagent` CLI or its spec differs, use the provided production snapshot and inspect compatibility before publishing. The framework checks exact names, typed contracts, product metadata and the deterministic verifier.

### Run an agent task locally with OpenRouter (optional)

The course RUSH Lab agent uses its configured **DeepSeek V4 Flash 0731** model and the TA-provided OpenRouter allowance; **you do not need an OpenRouter key to run the task's local pytest checks**. For a direct NanoAgent CLI agent run (outside RUSH), you do need a model credential and correct model ID:

1. Set `OPENROUTER_API_KEY` in **your terminal environment**, for example `export OPENROUTER_API_KEY=...` in WSL. Never commit a key in `.env`, source code, tests or a GitHub repository.
2. Copy `tests/agent_run.example.yaml` to a local config (or edit it in a private location) and replace the `model:` placeholder with the available **provider-qualified OpenRouter model ID**. The assignment names a model but does not provide a guaranteed API identifier.
3. Run the agent and inspect `result.json`, `verdict.json`, `reference.json`, `messages.json` and the `workspace/reports/result.json` artifact:

```bash
uv run --project /path/to/nanoagent-production/nanoagent nanoagent plugin agent \
  config=tests/agent_run.example.yaml home=/tmp/sql-query-repair-run
```

The example config assumes the current working directory is this plugin folder. For a second run, pick a new `home` directory. Its `max_steps` value permits reading, saving and submitting. The local model, pricing fields and limits are examples only; adjust to your actual account and the course instructions.

### Publish on RUSH Lab

1. Create **one separate GitHub repository for this folder**, push the contents including the lockfile and tests, and never include credentials.
2. Register the GitHub account with the TAs and confirm access at [rush-lab.org](https://rush-lab.org).
3. Use the installation command RUSH Lab presents (Windows users: run it inside WSL).
4. Publish the tested repository through the marketplace / `rush publish` workflow supplied by RUSH. If the platform rejects it, use NanoAgent's plugin inspection output to identify the precise packaging error and republish.
5. Run the task on RUSH; save **actual** arguments, run logs, output, verdict and validation/publishing logs for your PDF report.

### Reproducibility and limitations

- Task inputs are versioned JSON and all fixtures are code-defined and deterministic. No services or clock-dependent calls are required.
- A query is evaluated for semantic agreement on the three generated fixtures; it is not a proof of equivalence for every possible database. SQL is intentionally restricted to one SELECT without comments/semicolons. Execution uses SQLite, not PostgreSQL.
- Marketplace packaging checks alone do **not** prove verifier correctness. Use both the negative tests and actual hosted runs. Each RUSH run has its own workspace; a copied report from another workspace is not automatically trusted.
- Because this package was built in an environment without network access to upstream Git/PyPI, the real dependency installation, NanoAgent `plugin inspect` and live RUSH/OpenRouter agent run **must be rerun on your machine**. The included lockfile is adapted from the supplied Weather Alert reference, with this plugin's project name.
