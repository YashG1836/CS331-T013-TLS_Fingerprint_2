BUILD_DIR ?= build
PYTHON ?= python3

.PHONY: build test preflight check eval baseline clean
build:
	cmake -S . -B $(BUILD_DIR) -DCMAKE_BUILD_TYPE=Release
	cmake --build $(BUILD_DIR) --parallel

test: build
	ctest --test-dir $(BUILD_DIR) --output-on-failure
	$(PYTHON) -m pytest -q

PREFLIGHT_OUTPUT ?= results/preflight-current.json

preflight:
	$(PYTHON) code/scripts/preflight.py --output $(PREFLIGHT_OUTPUT)

check:
	$(PYTHON) code/scripts/evaluate.py --check-only

eval:
	$(PYTHON) code/scripts/evaluate.py --output results/evaluation.json

baseline:
	@test -n "$(CAPTURE_ID)" || (echo "usage: make baseline CAPTURE_ID=<registered-id>" >&2; exit 2)
	$(PYTHON) code/scripts/reference_baseline.py --capture-id "$(CAPTURE_ID)"

clean:
	rm -rf $(BUILD_DIR) .pytest_cache
