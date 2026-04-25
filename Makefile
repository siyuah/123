.PHONY: validate-v3 test-v3-contracts manifest-v3 smoke-v3-control-plane verify-v3-journal
MAKEFLAGS += --no-print-directory

validate-v3:
	python3 tools/validate_v3_bundle.py --write-report

test-v3-contracts:
	python3 -m unittest discover -s tests -p 'test_v3_*.py'
	$(MAKE) validate-v3

manifest-v3:
	python3 tools/update_v3_manifest.py

smoke-v3-control-plane:
	@if [ -n "$(JOURNAL)" ]; then \
		python3 tools/v3_control_plane_smoke.py --journal "$(JOURNAL)"; \
	else \
		python3 tools/v3_control_plane_smoke.py; \
	fi

verify-v3-journal:
	@if [ -z "$(JOURNAL)" ]; then \
		echo "JOURNAL is required: make verify-v3-journal JOURNAL=path/to/file.jsonl" >&2; \
		exit 2; \
	fi
	python3 tools/v3_control_plane.py verify-journal --journal "$(JOURNAL)"
