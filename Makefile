.PHONY: test test-coverage install-test-deps build-allinone run-allinone publish-docker install-cli

# --- Testing ---

install-test-deps:
	pip install -r tests/requirements.txt

test:
	pytest tests/

test-coverage:
	pytest tests/ --cov=api --cov=worker --cov=demoforge --cov-report=term-missing

test-verbose:
	pytest tests/ -vv

test-specific:
	pytest tests/$(TEST_FILE) -k $(TEST_NAME)

# --- Docker (all-in-one) ---

build-allinone:
	docker build -f docker/Dockerfile.allinone -t heygranth/demoforge:latest .

run-allinone:
	docker run --rm -p 8080:8080 --name demoforge heygranth/demoforge:latest

publish-docker:
	./scripts/docker-publish.sh $(VERSION)

# --- CLI ---

install-cli:
	pip install -e .
	@echo ""
	@echo "Run 'demoforge setup' to install the Playwright browser."

# --- Docker Compose (multi-container, development) ---

up:
	docker compose up --build -d

down:
	docker compose down -v

logs:
	docker compose logs -f
