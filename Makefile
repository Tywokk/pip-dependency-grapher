PYTHON ?= python3
CONFIG ?= config.ini

.PHONY: run test clean

run:
	PYTHONPATH=src $(PYTHON) -m depgraph --config $(CONFIG) $(ARGS)

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
