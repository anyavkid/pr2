CONFIG ?= examples/maven-central.ini
SHOW ?= graph

.PHONY: run test

run:
	PYTHONPATH=src python3 -m depgraph --config $(CONFIG) --show $(SHOW)

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -v
