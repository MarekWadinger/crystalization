# CEP manuscript (Elsevier elsarticle, two-column 5p). Run here or with
# `make -C papers/cep <target>`. Build artefacts stay here, git-ignored.
ROOT := ../..

.DEFAULT_GOAL := pdf
.PHONY: figures pdf check clean

figures: ## Redraw/copy the paper's figures into figures/
	cd $(ROOT) && uv run --frozen --group optics python scripts/paper_figures.py

pdf: figures ## Build main.pdf
	latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

check: ## CEP limits: pages, abstract words, highlights
	python3 $(ROOT)/scripts/paper_check.py

clean: ## Remove LaTeX artefacts and generated figures
	-latexmk -C main.tex
	rm -rf figures
