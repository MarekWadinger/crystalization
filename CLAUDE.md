# crystalization

Crystal-size measurement from a sight-glass camera on the Sereď seed pan (ZRA), part of the STU OPTIVISION project.

## Where things are

- **Paper:** [`papers/cep/ROADMAP.md`](papers/cep/ROADMAP.md): target, status, next steps. Read it before touching
  the paper, its figures or any number it reports. Build with `make -C papers/cep pdf`, then `make -C papers/cep check`.
- **AI use:** [`papers/cep/AI_USE.md`](papers/cep/AI_USE.md): rules, log and declaration.
- **Plant facts:** [`docs/sered/README.md`](docs/sered/README.md), [`datasets/README.md`](datasets/README.md); ask
  the `sered-plant-expert` agent.

## Rules

- Ground truth from the plant or the authors outranks model output.
- Scientific claim edits are proposed with their evidence for the author's approval, never applied silently.
- Every number and figure in the paper comes from a script and config in this repo.
- Pre-commit does not run tests: run `uv run pytest` before committing code.
