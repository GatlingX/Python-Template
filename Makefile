# ANSI color codes
GREEN=\033[0;32m
YELLOW=\033[0;33m
RED=\033[0;31m
BLUE=\033[0;34m
RESET=\033[0m

PYTHON=rye run python
TEST=rye run pytest
PROJECT_ROOT=.

########################################################
# Initialization: Delete later
########################################################

banner: check_rye
	@echo "$(YELLOW)🔍Generating banner...$(RESET)"
	@rye run python -m init.generate_banner
	@echo "$(GREEN)✅Banner generated.$(RESET)"


########################################################
# Check dependencies
########################################################

check_rye:
	@echo "$(YELLOW)🔍Checking rye version...$(RESET)"
	@if ! command -v rye > /dev/null 2>&1; then \
		echo "$(RED)rye is not installed. Please install rye before proceeding.$(RESET)"; \
		exit 1; \
	else \
		rye --version; \
	fi

check_jq:
	@echo "$(YELLOW)🔍Checking jq version...$(RESET)"
	@if ! command -v jq > /dev/null 2>&1; then \
		echo "$(RED)jq is not installed. Please install jq before proceeding.$(RESET)"; \
		echo "$(RED)brew install jq$(RESET)"; \
		exit 1; \
	else \
		jq --version; \
	fi

check_prek:
	@echo "$(YELLOW)🔍Checking prek version...$(RESET)"
	@if ! command -v prek > /dev/null 2>&1; then \
		echo "$(RED)prek is not installed. Please install prek before proceeding.$(RESET)"; \
		echo "$(RED)curl --proto '=https' --tlsv1.2 -LsSf https://github.com/j178/prek/releases/download/v0.3.3/prek-installer.sh | sh$(RESET)"; \
		exit 1; \
	else \
		prek --version; \
	fi

########################################################
# Setup githooks for linting
########################################################
install_hooks: check_prek
	@echo "$(YELLOW)🔨Installing pre-commit hooks with prek...$(RESET)"
	@git config --unset core.hooksPath || true
	@prek install


########################################################
# Python dependency-related
########################################################

update_python_dep: check_rye
	@echo "$(YELLOW)🔄Updating python dependencies...$(RESET)"
	@rye sync

view_python_venv_size:
	@echo "$(YELLOW)🔍Checking python venv size...$(RESET)"
	@PYTHON_VERSION=$$(cat .python-version | cut -d. -f1,2) && \
	cd .venv/lib/python$$PYTHON_VERSION/site-packages && du -sh . && cd ../../../
	@echo "$(GREEN)Python venv size check completed.$(RESET)"

view_python_venv_size_by_libraries:
	@echo "$(YELLOW)🔍Checking python venv size by libraries...$(RESET)"
	@PYTHON_VERSION=$$(cat .python-version | cut -d. -f1,2) && \
	cd .venv/lib/python$$PYTHON_VERSION/site-packages && du -sh * | sort -h && cd ../../../
	@echo "$(GREEN)Python venv size by libraries check completed.$(RESET)"

########################################################
# Run Main Application
########################################################

all: update_python_dep install_hooks
	@echo "$(GREEN)🏁Running main application...$(RESET)"
	@$(PYTHON) main.py
	@echo "$(GREEN)✅ Main application run completed.$(RESET)"


########################################################
# Run Tests
########################################################

TEST_TARGETS = tests/

# Tests
test: check_rye
	@echo "$(GREEN)🧪Running Target Tests...$(RESET)"
	$(TEST) $(TEST_TARGETS)
	@echo "$(GREEN)✅Target Tests Passed.$(RESET)"


########################################################
# Cleaning
########################################################

# Linter will ignore these directories
IGNORE_LINT_DIRS = .venv|venv
LINE_LENGTH = 88

lint: check_prek
	@echo "$(YELLOW)🔍Running pre-commit hooks...$(RESET)"
	@prek run --all-files
	@echo "$(GREEN)✅Pre-commit hooks passed.$(RESET)"

fmt: check_rye check_jq
	@echo "$(YELLOW)✨Formatting project with Black...$(RESET)"
	@rye run black --exclude '/($(IGNORE_LINT_DIRS))/' . --line-length $(LINE_LENGTH)
	@echo "$(YELLOW)✨Formatting JSONs with jq...$(RESET)"
	@count=0; \
	find . \( $(IGNORE_LINT_DIRS:%=-path './%' -prune -o) \) -type f -name '*.json' -print0 | \
	while IFS= read -r -d '' file; do \
		if jq . "$$file" > "$$file.tmp" 2>/dev/null && mv "$$file.tmp" "$$file"; then \
			count=$$((count + 1)); \
		else \
			rm -f "$$file.tmp"; \
		fi; \
	done; \
	echo "$(BLUE)$$count JSON file(s)$(RESET) formatted."; \
	echo "$(GREEN)✅Formatting completed.$(RESET)"

vulture: check_rye
	@echo "$(YELLOW)🔍Running Vulture...$(RESET)"
	@rye run vulture .
	@echo "$(GREEN)✅Vulture completed.$(RESET)"

########################################################
# Dependencies
########################################################

requirements:
	@echo "$(YELLOW)🔍Checking requirements...$(RESET)"
	@cp requirements-dev.lock requirements.txt
	@echo "$(GREEN)✅Requirements checked.$(RESET)"
