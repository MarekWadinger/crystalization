# AI use

Elsevier [generative-AI policy](https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals):

- Every author logs each substantive AI contribution below, with any tool (grammar fixes and code autocomplete
  excepted). The declaration is written from the log.
- AI must not create or alter primary-data images (frames, micrographs).

Declaration: unnumbered section before the references.

> **Declaration of generative AI and AI-assisted technologies in the manuscript preparation process.**
> During the preparation of this work the authors used [tools] in order to [tasks from the log]. After using
> these tools, the authors reviewed and edited the content as needed and take full responsibility for the content
> of the published article.

## Log

| Date | Tool | Task | Output | Human check |
| --- | --- | --- | --- | --- |
| 2026-03-30 – 2026-11-03 | Claude Code | Analysis code and docs (97 of 133 commits have a Claude trailer) | `src/`, `scripts/`, `docs/` | Pending: which manuscript parts were AI-drafted |
| 2026-11-03 | Claude Code | Venue choice, CEP fit reviews, submission plan | target in [`main.tex`](main.tex) | Author chose CEP |
| 2026-11-03 | Claude Code | Roadmap, agent instructions, MIT licence file; CRediT draft and ORCID lookup | [`ROADMAP.md`](ROADMAP.md), [`CLAUDE.md`](../../CLAUDE.md), [`LICENSE`](../../LICENSE), [`CREDIT.md`](CREDIT.md) | Author reviewed; each co-author confirms their CRediT row |
