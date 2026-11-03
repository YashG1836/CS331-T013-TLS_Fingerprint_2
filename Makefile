BUILD_DIR ?= build
PYTHON ?= python3

.PHONY: build test check eval clean
build:
	cmake -S . -B $(BUILD_DIR) -DCMAKE_BUILD_TYPE=Release
	cmake --build $(BUILD_DIR) --parallel

test: build
	ctest --test-dir $(BUILD_DIR) --output-on-failure
	$(PYTHON) -m pytest -q

check:
	$(PYTHON) code/scripts/evaluate.py --check-only

eval:
	$(PYTHON) code/scripts/evaluate.py --output results/evaluation.json

clean:
	rm -rf $(BUILD_DIR) .pytest_cache
