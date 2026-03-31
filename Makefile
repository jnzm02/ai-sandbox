# Makefile for RAG API - Development & Deployment
# Senior AI Systems Engineer pattern: Make everything one command

.PHONY: help install ingest query chat api test lint docker-build docker-run docker-stop deploy-setup deploy clean

# Default target
help:
	@echo "RAG API - Available Commands"
	@echo "============================"
	@echo ""
	@echo "Local Development:"
	@echo "  make install       - Install dependencies"
	@echo "  make ingest        - Index FastAPI documentation"
	@echo "  make query         - Run CLI query interface"
	@echo "  make chat          - Run CLI chat interface"
	@echo "  make api           - Run local API server"
	@echo "  make test          - Run linting and type checks"
	@echo "  make lint          - Run flake8 linter"
	@echo ""
	@echo "Docker (Local):"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-run    - Run container locally"
	@echo "  make docker-stop   - Stop container"
	@echo "  make docker-logs   - View container logs"
	@echo "  make docker-shell  - Access container shell"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy-init   - Initialize deployment files"
	@echo "  make docker-push   - Push image to Docker Hub"
	@echo "  make deploy-scripts - Make deployment scripts executable"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean         - Clean temporary files"
	@echo "  make backup        - Create local backup"
	@echo ""

# ============================================================================
# Local Development
# ============================================================================

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

ingest:
	@echo "Running ingestion pipeline..."
	python src/ingest.py
	@echo "✅ Vector database indexed"

query:
	@echo "Starting query CLI..."
	python src/query.py

chat:
	@echo "Starting chat CLI..."
	python src/chat.py

api:
	@echo "Starting local API server on http://localhost:8000"
	@echo "Docs: http://localhost:8000/docs"
	python src/api.py

test: lint
	@echo "Running import tests..."
	python -c "import src.ingest; import src.query; import src.chat; import src.api"
	@echo "✅ All tests passed"

lint:
	@echo "Running flake8..."
	flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 src/ --count --max-complexity=10 --max-line-length=100 --statistics
	@echo "✅ Linting passed"

# ============================================================================
# Docker (Local Testing)
# ============================================================================

docker-build:
	@echo "Building Docker image..."
	docker build -t rag-api:latest .
	@echo "✅ Docker image built: rag-api:latest"

docker-run: docker-build
	@echo "Starting container..."
	docker run -d \
		--name rag-api \
		-p 8000:8000 \
		-v $(PWD)/data/chroma_db:/app/data/chroma_db:ro \
		--env-file .env \
		rag-api:latest
	@echo "✅ Container running on http://localhost:8000"
	@echo "Health: curl http://localhost:8000/health"

docker-stop:
	@echo "Stopping container..."
	-docker stop rag-api
	-docker rm rag-api
	@echo "✅ Container stopped"

docker-logs:
	docker logs -f rag-api

docker-shell:
	docker exec -it rag-api /bin/bash

# ============================================================================
# Deployment
# ============================================================================

deploy-init:
	@echo "Initializing deployment configuration..."
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "⚠️  Created .env from template - please add your ANTHROPIC_API_KEY"; \
	else \
		echo "✅ .env already exists"; \
	fi
	@make deploy-scripts
	@echo ""
	@echo "✅ Deployment files ready"
	@echo ""
	@echo "Next steps:"
	@echo "1. Add your ANTHROPIC_API_KEY to .env"
	@echo "2. Run 'make ingest' to create vector database"
	@echo "3. Push to Docker Hub: make docker-push"
	@echo "4. Follow DEPLOYMENT_VPS.md for server setup"

deploy-scripts:
	@echo "Making deployment scripts executable..."
	chmod +x deploy/*.sh
	@echo "✅ Scripts are executable"

docker-push:
	@if [ -z "$(DOCKER_USER)" ]; then \
		echo "Error: Set DOCKER_USER environment variable"; \
		echo "Usage: DOCKER_USER=your-username make docker-push"; \
		exit 1; \
	fi
	@echo "Building and pushing to Docker Hub..."
	docker build -t $(DOCKER_USER)/rag-api:latest .
	docker push $(DOCKER_USER)/rag-api:latest
	@echo "✅ Image pushed: $(DOCKER_USER)/rag-api:latest"

# ============================================================================
# Utilities
# ============================================================================

clean:
	@echo "Cleaning temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleaned"

backup:
	@echo "Creating local backup..."
	@mkdir -p backups
	@BACKUP_NAME="chroma_db_$$(date +%Y%m%d_%H%M%S).tar.gz"; \
	tar -czf backups/$$BACKUP_NAME data/chroma_db; \
	echo "✅ Backup created: backups/$$BACKUP_NAME"

# ============================================================================
# Advanced: Docker Compose
# ============================================================================

compose-up:
	docker-compose up -d
	@echo "✅ Services started with docker-compose"

compose-down:
	docker-compose down
	@echo "✅ Services stopped"

compose-logs:
	docker-compose logs -f

# ============================================================================
# Development Helpers
# ============================================================================

check-env:
	@echo "Checking environment..."
	@if [ ! -f .env ]; then \
		echo "❌ .env file not found"; \
		exit 1; \
	fi
	@if ! grep -q "ANTHROPIC_API_KEY=sk-ant-" .env 2>/dev/null; then \
		echo "⚠️  Warning: ANTHROPIC_API_KEY may not be set in .env"; \
	else \
		echo "✅ .env configured"; \
	fi
	@if [ ! -d data/chroma_db ]; then \
		echo "❌ Vector database not found (run 'make ingest')"; \
		exit 1; \
	else \
		echo "✅ Vector database exists"; \
	fi

dev: check-env
	@echo "Starting development environment..."
	@make api

# Quick deploy to server (requires SSH access configured)
# Usage: SERVER=user@host make remote-deploy
remote-deploy:
	@if [ -z "$(SERVER)" ]; then \
		echo "Error: Set SERVER environment variable"; \
		echo "Usage: SERVER=root@your-server-ip make remote-deploy"; \
		exit 1; \
	fi
	@echo "Deploying to $(SERVER)..."
	ssh $(SERVER) "cd /opt/rag-api && ./deploy.sh --pull"
	@echo "✅ Deployment triggered on $(SERVER)"
