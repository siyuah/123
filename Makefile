.PHONY: validate-v3 test-v3-contracts manifest-v3

validate-v3:
	python3 tools/validate_v3_bundle.py --write-report

test-v3-contracts: validate-v3

manifest-v3:
	python3 tools/update_v3_manifest.py
