BUILD_DIR ?= build
PYTHON ?= python3

.PHONY: build test preflight check eval baseline lab-image lab-eval lab-capture lab-versions clean
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

LAB_IMAGE ?= cn-lab
LAB_RUN = docker run --rm -v "$(CURDIR)":/lab $(LAB_IMAGE)

lab-image:
	docker build -t $(LAB_IMAGE) -f code/Dockerfile code

lab-eval:
	$(LAB_RUN) python3 code/scripts/analyze.py --output-dir results/reproduced

lab-versions:
	mkdir -p results/reproduced
	$(LAB_RUN) bash code/scripts/versions.sh > results/reproduced/versions.txt

lab-capture:
	@test -n "$(CAPTURE_ID)" || (echo "usage: make lab-capture CAPTURE_ID=<track1-id>" >&2; exit 2)
	docker run --rm --cap-add NET_ADMIN -v "$(CURDIR)":/lab $(LAB_IMAGE) python3 code/scripts/capture.py --capture-id "$(CAPTURE_ID)" --confirm-network

clean:
	rm -rf $(BUILD_DIR) .pytest_cache
