# GawdZilla — Makefile

.PHONY: help venv install run pack clean docker

help:
	@echo "GawdZilla targets:"
	@echo "  make venv     - create .venv"
	@echo "  make install  - install deps"
	@echo "  make run      - start the launcher"
	@echo "  make pack     - build source zip"
	@echo "  make clean    - remove build artifacts"
	@echo "  make docker   - build and start container"

venv:
	python3 -m venv .venv

install: venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

run:
	.venv/bin/python3 GawdZilla.py

pack:
	./pack.sh

clean:
	rm -rf .venv build dist
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

docker:
	docker compose up -d --build
