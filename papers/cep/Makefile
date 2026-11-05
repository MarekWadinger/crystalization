# CEP manuscript (Elsevier elsarticle, two-column 5p). Run here or with
# `make -C papers/cep <target>`. Build artefacts stay here, git-ignored.
ROOT := ../..

.DEFAULT_GOAL := pdf
.PHONY: figures pdf ga check clean

figures: ## Redraw/copy the paper's figures into figures/
	cd $(ROOT) && uv run --frozen --group optics python scripts/paper_figures.py

pdf: figures ## Build main.pdf
	latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

ga: ## Graphical abstract, a separate upload (not typeset: it would add a page)
	cd $(ROOT) && uv run --frozen --group optics python scripts/graphical_abstract.py

check: ## CEP limits: pages, abstract words, highlights
	python3 $(ROOT)/scripts/paper_check.py

clean: ## Remove LaTeX artefacts and generated figures
	-latexmk -C main.tex
	rm -rf figures
