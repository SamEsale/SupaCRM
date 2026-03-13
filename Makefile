# Simple Makefile for common tasks
.PHONY: help

help:
	@echo "Available targets: help, lint, test"

lint:
	@echo "Run linter (configure as needed)"

test:
	@echo "Run tests (use pytest in backend)"
