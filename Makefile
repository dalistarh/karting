# One command rebuilds everything from data/:   make all
# Fresh checkout:                                make setup && make all

PY := .venv/bin/python

.PHONY: setup fetch prepare trace all clean

setup:
	uv venv --python python3.11 .venv
	uv pip install --python .venv/bin/python -r requirements.txt

fetch:
	$(PY) scripts/fetch_ortho.py

prepare: fetch
	$(PY) scripts/prepare.py

trace: prepare
	$(PY) scripts/trace.py
	$(PY) scripts/trace_check.py

all: trace

clean:
	rm -rf build
