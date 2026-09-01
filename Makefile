.PHONY: publish publish-install sync-plugin help

PYTHON ?= python3

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

publish: ## Publish all convention docs to Confluence
	$(PYTHON) .github/publish.py

publish-install: ## Install Python dependencies
	pip install -r requirements.txt

sync-plugin: ## Package ADRs into the Claude plugin skill (adr-lookup)
	$(PYTHON) scripts/package_claude_plugin.py
