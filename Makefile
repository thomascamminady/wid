YEAR ?= 2024

.PHONY: help install hooks data plot-line plot-donut plot-bar-donut plot-percentiles plot-percentiles-zoom plot-percentiles-staircase plot-wealth-donut plots format lint check clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install: ## Create the virtual environment from uv.lock
	uv sync

hooks: ## Install the pre-commit hooks
	uv run pre-commit install

data: ## Download Germany from the WID bulk zip and write the tidy CSV
	uv run fetch-data

plot-line: ## Log-x line chart of top wealth shares (YEAR=2024)
	uv run plot-line --year $(YEAR)

plot-donut: ## Donuts: share of adults vs. share of wealth (YEAR=2024)
	uv run plot-donut --year $(YEAR)

plot-bar-donut: ## Wealth donut with the top 1% split up in a bar (YEAR=2024)
	uv run plot-bar-donut --year $(YEAR)

plot-percentiles: ## Average wealth in each percentile of adults (YEAR=2024)
	uv run plot-percentiles --year $(YEAR)

plot-percentiles-zoom: ## Percentile chart plus a zoom into the top 1% (YEAR=2024)
	uv run plot-percentiles-zoom --year $(YEAR)

plot-percentiles-staircase: ## Percentile zooms as a staircase with zoom lines (YEAR=2024)
	uv run plot-percentiles-staircase --year $(YEAR)

plot-wealth-donut: ## Wealth donut with the top 1% arc in purple shades (YEAR=2024)
	uv run plot-wealth-donut --year $(YEAR)

plots: plot-line plot-donut plot-bar-donut plot-percentiles plot-percentiles-zoom plot-percentiles-staircase plot-wealth-donut ## All charts

format: ## Format with ruff
	uv run ruff format src

lint: ## Lint with ruff and type-check with ty
	uv run ruff check src
	uv run ty check

check: ## Run every pre-commit hook on all files
	uv run pre-commit run --all-files

clean: ## Remove generated outputs and the raw download
	rm -rf output data/raw
