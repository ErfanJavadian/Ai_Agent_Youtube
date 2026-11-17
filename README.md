# AI YouTube Autonomous System

A GitHub-first, low-cost system for producing English-language faceless YouTube documentaries about AI, science, technology, and the future of humanity.

> **V1 is an assisted production pipeline, not a fully autonomous AI video generator.** It does not call external AI APIs or the YouTube Data API. Judgment-heavy work can be prepared as structured task packets for a human-operated AI chat interface, then brought back into the project.

## V1 goals

- Track a video project through explicit, recoverable workflow states.
- Keep research sources, factual claims, scripts, storyboards, assets, and render metadata structured.
- Build a deterministic foundation for graphics-led video production.
- Preserve source and asset licensing metadata.
- Require human approval before publication.
- Prepare a publishing package for manual upload through YouTube Studio.

## Constraints and non-goals

- No external AI APIs and no YouTube Data API.
- No promise of automatic YouTube publishing in V1.
- GitHub is the source of truth for code and project definitions; it is not assumed to be an always-on application server.
- GitHub Actions jobs must remain bounded and will be evaluated before attempting video rendering.
- Heavy local video generation or large language models are outside the initial scope.
- Generated media and large render outputs should not be committed to this source repository.

## Repository map

- `docs/ARCHITECTURE_V1.md` — approved V1 architecture blueprint.
- `schemas/` — machine-readable project and workflow contracts.
- `src/ai_yas/` — Python application package (foundation only at this stage).
- `tests/` — standard-library foundation tests.
- `.github/workflows/` — continuous integration.

## Current status

Phase 0 — Foundation is being established. The schemas and package are contracts and scaffolding; production engines are not implemented yet.

## Development

Requires Python 3.11 or newer.

Run the foundation tests:

```bash
python -m unittest discover -s tests -v
```

No third-party runtime dependency is required for the current foundation tests.

## Workflow principles

1. Validate project data at system boundaries.
2. Use explicit states and bounded transitions.
3. Preserve provenance for research and media assets.
4. Treat retrieved documents and generated model output as untrusted input.
5. Keep external actions separate from planning and require human approval for publication.

See [V1 Architecture](docs/ARCHITECTURE_V1.md) for system boundaries, contracts, and the phased implementation plan.
