# AI YouTube Autonomous System

A GitHub-first, low-cost assisted production system for English-language faceless documentaries about AI, science, technology, and the future of humanity.

> **V1 is an assisted production pipeline, not a fully autonomous AI video generator.** It does not call external AI APIs or the YouTube Data API. Judgment-heavy work can be prepared as structured task packets for a human-operated AI chat interface, then imported and validated.

## Current implementation

- **Phase 0 — Foundation:** repository metadata, JSON contracts, and CI.
- **Phase 1 — Core Workflow Engine:** project creation, JSON persistence, explicit stage transitions, failure/block recovery, and a mandatory human approval gate.

Production engines (research, scriptwriting, graphics, audio, rendering, analytics) are not implemented yet.

## Constraints

- No external AI APIs and no YouTube Data API.
- No automatic publishing promise; V1 prepares a package for manual YouTube Studio upload.
- GitHub is source control and CI, not an always-on application server.
- GitHub Actions video rendering feasibility must be tested before use.
- Large generated media and render outputs must stay outside this source repository.

## Repository map

- `docs/ARCHITECTURE_V1.md` — V1 architecture blueprint.
- `schemas/` — machine-readable project and workflow contracts.
- `src/ai_yas/storage.py` — atomic JSON project storage.
- `src/ai_yas/workflow.py` — deterministic workflow state machine.
- `tests/` — foundation and workflow integration tests.
- `.github/workflows/tests.yml` — Python 3.11/3.12 CI.

## Quick start

Requires Python 3.11 or newer.

```bash
python -m unittest discover -s tests -v
```

Example:

```python
from ai_yas import ProjectStore, WorkflowEngine

engine = WorkflowEngine(ProjectStore("./workspace/projects"))
engine.create_project(
    project_id="first-documentary",
    title="The Future of AI",
    target_audience="Curious general audience",
    topic="How AI may change science",
)
engine.start("first-documentary")
engine.complete_current_stage("first-documentary", checkpoint_ref="intake/brief.json")
```

A project starts at the `intake` stage. Each stage must be started and explicitly completed. At the final `approval` stage, a human must approve before the workflow can be completed.

## Workflow stages

`intake → research → strategy → script → storyboard → assets → audio → edit → quality_control → publishing_package → approval → complete`

A failed or blocked workflow can be retried after its cause is addressed. Every transition is persisted to the project's JSON files.

## Operational notes

- Storage writes use temporary files and atomic replacement.
- Project IDs are restricted to safe characters to prevent path traversal.
- Concurrent writes to the same project are **not supported** in this version.
- The current tests use Python's standard library; no network access or external API credentials are needed.

See [V1 Architecture](docs/ARCHITECTURE_V1.md) for system boundaries and phased scope.
