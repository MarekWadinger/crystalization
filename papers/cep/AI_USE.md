# AI use

Elsevier [generative-AI policy](https://www.elsevier.com/about/policies-and-standards/generative-ai-policies-for-journals):

- Every author logs each substantive AI contribution below, with any tool (grammar fixes and code autocomplete
  excepted). The declaration is written from the log.
- AI must not create or alter primary-data images (frames, micrographs).

Declaration: unnumbered section before the references.

> **Declaration of generative AI and AI-assisted technologies in the manuscript preparation process.**
> During the preparation of this work the authors used Claude Code with Claude models (Anthropic) in order to write
> and test analysis and estimator code, search for and verify literature, draft and revise the manuscript text, and
> simulate peer review and notation audits. [Draft from the log; each author confirms.] After using
> these tools, the authors reviewed and edited the content as needed and take full responsibility for the content
> of the published article.

## Log

| Date | Tool | Task | Output | Human check |
| --- | --- | --- | --- | --- |
| 2026-03-30 – 2026-11-03 | Claude Code | Analysis code and docs (97 of 133 commits have a Claude trailer) | `src/`, `scripts/`, `docs/` | Pending: which manuscript parts were AI-drafted |
| 2026-11-03 | Claude Code | Venue choice, CEP fit reviews, submission plan | target in [`main.tex`](main.tex) | Author chose CEP |
| 2026-11-03 | Claude Code | Roadmap, agent instructions, MIT licence file; CRediT draft and ORCID lookup | [`ROADMAP.md`](ROADMAP.md), [`CLAUDE.md`](../../CLAUDE.md), [`LICENSE`](../../LICENSE), [`CREDIT.md`](CREDIT.md) | Author reviewed; each co-author confirms their CRediT row |
| 2026-11-04 | Claude Code (Claude models, Anthropic): supervisor, plant-expert and optics-expert agents | Analysis round that froze the research problem, estimand, measurement model terms and section map | reframe brief (session scratchpad); [`ROADMAP.md`](ROADMAP.md) "Why" | Author approved the round-1–3 decisions (title, Lemma 1, ln G state, estimand, constant-θ requirement) |
| 2026-11-04 | Claude Code: thesis-writer agent | Restructured and rewrote the manuscript around the soft sensor (sections, appendices, abstract, highlights, cover letter); four review-fix rounds | `papers/cep/` | Every claim-level edit logged for approval in [`CLAIM_CHANGES.md`](CLAIM_CHANGES.md) items 77–; open items pending author review |
| 2026-11-04 | Claude Code: estimator agent | EKF, leave-one-strike-out evaluation, process-signal baseline, anchor-noise bootstrap, watershed seed sweep, camera-signal script, with unit tests | `src/softsensor/`, `scripts/softsensor_results.py`, `scripts/softsensor_process_baseline.py`, `scripts/microscope_anchor_noise.py`, `scripts/watershed_seed_sweep.py`, `docs/softsensor/`, `tests/test_softsensor.py` | Tests run (21 soft-sensor tests); author review of the code pending |
| 2026-11-04 | Claude Code: citation-finder agent | Literature search for soft sensors, estimators, identifiability, Cellpose and sugar-pan imaging; metadata checked against Crossref (DOI resolves) and each use limited to its abstract or full text | `references.bib` (24 entries added); scratchpad reference lists | Authors to spot-check the trade-journal entries without DOI (BoucheGaillac2015, Honkanen2023) |
| 2026-11-04 | Claude Code: peer-reviewer, opponent, bridging-reviewer and notation-checker agents | Simulated referee review, narrative and notation audits that drove review rounds 2–4 | review notes (session scratchpad) | Author decided which findings to apply |
| 2026-11-05 | Claude Code (main session, web-fetch agents) | Camera identification from Ademco manuals, the Oxford Sony CCD table and the plant e-mail; rewrote App. A §camera and added the transfer paragraph; added the photo panel to Fig. A.2 (script crop and labels only, no generative image editing) | `papers/cep/sections/appendix_optics.tex`, `references.bib`, `src/optics/optical_layout.py`, `docs/lens/README.md`, `configs/camera_100.toml` (comments, source tags) | Claim edits logged in [`CLAIM_CHANGES.md`](CLAIM_CHANGES.md) item 155; author asked for each step |
