.PHONY: test test-coverage install-test-deps

install-test-deps:
	pip install -r tests/requirements.txt

test:
	pytest tests/

test-coverage:
	pytest tests/ --cov=api --cov=worker --cov-report=term-missing

test-verbose:
	pytest tests/ -vv

test-specific:
	pytest tests/$(TEST_FILE) -k $(TEST_NAME)
