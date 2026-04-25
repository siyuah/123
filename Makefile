.PHONY: validate-v3 test-v3-contracts manifest-v3 smoke-v3-control-plane verify-v3-journal release-readiness-v3 release-dry-run-v3 release-dry-run-v3-remote-ci release-dry-run-v3-remote-ci-strict release-evidence-v3 release-evidence-v3-remote-ci
MAKEFLAGS += --no-print-directory
TAG ?= v3.0.0-rc1
RELEASE_READINESS_FLAGS ?=

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
	@python3 tools/v3_control_plane.py verify-journal --journal "$(JOURNAL)"

release-readiness-v3:
	@python3 tools/v3_release_readiness.py --require-clean-git $(RELEASE_READINESS_FLAGS)

release-dry-run-v3:
	@python3 tools/v3_release_dry_run.py --tag $(TAG) --require-clean-git

release-dry-run-v3-remote-ci:
	@python3 tools/v3_release_dry_run.py --tag $(TAG) --require-clean-git --include-remote-ci

release-dry-run-v3-remote-ci-strict:
	@python3 tools/v3_release_dry_run.py --tag $(TAG) --require-clean-git --include-remote-ci --require-remote-ci-success

release-evidence-v3:
	@python3 tools/v3_release_evidence.py --tag $(TAG) --require-clean-git

release-evidence-v3-remote-ci:
	@python3 tools/v3_release_evidence.py --tag $(TAG) --require-clean-git --include-remote-ci
