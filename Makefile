.PHONY: test release

test:
	@echo "Running unit tests..." 
	@python3 -m unittest tests.test_anchor -v

release:
	@bash scripts/release.sh v0.1.0
