YEAR ?= 2024

.PHONY: help install data plot-line plot-donut plots format lint check clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install: ## Create the virtual environment from uv.lock
	uv sync

data: ## Download Germany from the WID bulk zip and write the tidy CSV
	uv run fetch-data

plot-line: ## Log-x line chart of top wealth shares (YEAR=2024)
	uv run plot-line --year $(YEAR)

plot-donut: ## Donuts: share of adults vs. share of wealth (YEAR=2024)
	uv run plot-donut --year $(YEAR)

plots: plot-line plot-donut ## All charts

format: ## Format with ruff
	uv run ruff format src

lint: ## Lint with ruff and type-check with ty
	uv run ruff check src
	uv run ty check src

check: format lint ## Format, lint and type-check

clean: ## Remove generated outputs and the raw download
	rm -rf output data/raw
