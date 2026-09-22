PROJECT := webber
SCRIPTS_DIR := scripts
SRC_ROOT_DIR := src
PYTHON_VERSION ?= 3
PYTHON ?= python$(PYTHON_VERSION)
ARGS ?=

build: | dist

install: build
	@echo "Installing $(PROJECT)..."
	@pipx install ./dist/$(PROJECT)-*.whl

uninstall:
	@echo "Uninstalling $(PROJECT)..."
	@pipx uninstall $(PROJECT)

run:
	@$(SCRIPTS_DIR)/run_in_venv.sh $(PYTHON) $(SRC_ROOT_DIR)/$(PROJECT)/main.py $(ARGS)

profile:
	@$(SCRIPTS_DIR)/run_in_venv.sh $(PYTHON) -m cProfile -s cumulative $(SRC_ROOT_DIR)/$(PROJECT)/main.py $(ARGS)

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf dist build $(SRC_ROOT_DIR)/$(PROJECT).egg-info

dist:
	@echo "Building $(PROJECT)..."
	@mv src/webber/__debug__.py /tmp/.
	$(SCRIPTS_DIR)/run_in_venv.sh $(PYTHON) -m build --wheel
	rm -rf build **/*.egg-info
	@mv /tmp/__debug__.py src/webber/.

checkin:
	@git diff . | grep -E '^[\+\-][^\+\-]+' | head -n 20 > /tmp/git_diff_summary.txt
	@date > TIMESTAMP
	git pull && git add . && git commit -F /tmp/git_diff_summary.txt && git push

tree:
	@tree -CF --dirsfirst --charset=utf8 -I __pycache__

help:
	@echo "Usage: make [target]"
	@echo "Available targets:"
	@echo "  build      Build the $(PROJECT) package"
	@echo "  checkin    Commit and push changes to the repository"
	@echo "  install    Install the $(PROJECT) package using pipx"
	@echo "  uninstall  Uninstall the $(PROJECT) package using pipx"
	@echo "  run        Run the $(PROJECT) script with optional arguments"
	@echo "  clean      Clean build artifacts"
	@echo "  tree       Display the project directory tree"
	@echo "  help       Show this help message"
	@echo "  profile    Run the $(PROJECT) script with cProfile for performance analysis (debug only)"

.PHONY: build install uninstall run profile clean dist checkin tree help
