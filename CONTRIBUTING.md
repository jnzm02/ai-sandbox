# Contributing to FastAPI RAG System

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/YOUR_USERNAME/ai-sandbox.git
   cd ai-sandbox
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Environment**
   ```bash
   cp .env.example .env
   # Add your ANTHROPIC_API_KEY to .env
   ```

4. **Index Documents**
   ```bash
   python3 src/ingest.py
   ```

5. **Run Tests**
   ```bash
   python3 test_api.py
   ```

## Code Style

- Follow PEP 8
- Use type hints where possible
- Add docstrings to functions
- Keep functions focused and small

## Pull Request Process

1. Create a new branch: `git checkout -b feature/your-feature-name`
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Update README.md if needed
6. Commit with clear messages
7. Push to your fork
8. Open a Pull Request

## Areas for Contribution

### High Priority
- [ ] Add evaluation metrics (precision, recall)
- [ ] Implement hybrid search (BM25 + semantic)
- [ ] Add reranking with cross-encoder
- [ ] Write comprehensive unit tests
- [ ] Add streaming responses

### Medium Priority
- [ ] Implement rate limiting
- [ ] Add authentication/authorization
- [ ] Redis session persistence
- [ ] Prometheus metrics
- [ ] Load testing suite

### Low Priority
- [ ] Support multiple LLM providers
- [ ] Add multi-language support
- [ ] Web UI frontend
- [ ] Batch processing API
- [ ] Export conversation history

## Reporting Issues

When reporting issues, please include:
- Python version
- OS/platform
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs

## Questions?

Open an issue with the "question" label.

## Code of Conduct

Be respectful, inclusive, and constructive in all interactions.
