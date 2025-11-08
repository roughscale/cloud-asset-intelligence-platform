# Testing Guide

## Overview

We've implemented a comprehensive test suite that would have caught the import errors we experienced during deployment.

## What We Built

### Test Infrastructure

1. **Test Fixtures** (`backend/tests/conftest.py`)
   - Mock Neo4j and Redis clients
   - Sample assets and enrichments
   - Mock AWS Config data
   - FastAPI test client with dependency injection

2. **Test Suites**
   - `test_imports.py` - **Catches import/module errors**
   - `test_models.py` - Data model validation
   - `test_api.py` - API endpoint testing
   - `test_collectors.py` - AWS collector testing

3. **CI/CD Integration**
   - GitHub Actions workflow
   - Runs on every push and PR
   - Multiple Python versions (3.11, 3.12)
   - Code coverage reporting

### Test Categories

- **Unit Tests** - Fast, isolated tests (< 100ms each)
- **Integration Tests** - Tests with real Neo4j/Redis
- **Import Tests** - Verify all modules can be imported

## How Tests Would Have Caught Our Errors

### Error 1: Missing `close_neo4j_client` export

**What happened:**
```python
ImportError: cannot import name 'close_neo4j_client' from 'app.db'
```

**Test that catches it:**
```python
# tests/test_imports.py
def test_import_db_clients():
    from app.db import close_neo4j_client  # This would fail
    assert close_neo4j_client is not None
```

### Error 2: Missing `app.tasks` module

**What happened:**
```python
ModuleNotFoundError: No module named 'app.tasks'
```

**Test that catches it:**
```python
# tests/test_imports.py
def test_import_main_app():
    from app.main import app  # This imports tasks, would fail
    assert app is not None
```

## Running Tests

### In Development (Local)

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run import tests (quick sanity check)
make test-imports

# Run all tests
make test

# Run with coverage
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### In Docker

```bash
# Run tests in container
docker compose exec backend pytest

# Run specific test
docker compose exec backend pytest tests/test_imports.py -v

# Run with coverage
docker compose exec backend pytest --cov=app
```

### Pre-commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
cd backend
pytest tests/test_imports.py
if [ $? -ne 0 ]; then
    echo "Import tests failed. Fix errors before committing."
    exit 1
fi
```

## Test Coverage Goals

| Component | Target Coverage | Critical Paths |
|-----------|----------------|----------------|
| Models | 90%+ | 100% |
| API Endpoints | 85%+ | 95% |
| Collectors | 80%+ | 90% |
| Services | 85%+ | 95% |
| **Overall** | **85%** | **95%** |

## Best Practices

### 1. **Always Run Import Tests First**

```bash
# Before starting services
make test-imports

# Before committing
pytest tests/test_imports.py
```

### 2. **Write Tests Before Fixing Bugs**

When you find a bug:
1. Write a test that reproduces it
2. Verify test fails
3. Fix the bug
4. Verify test passes
5. Commit both test and fix

### 3. **Use Test-Driven Development (TDD)**

For new features:
1. Write the test first
2. Run it (should fail)
3. Implement the feature
4. Run test (should pass)
5. Refactor if needed

## Example: TDD for New Feature

Let's say you want to add asset filtering by tag:

**Step 1: Write the test first**
```python
# tests/test_api.py
def test_filter_assets_by_tag(test_client, mock_neo4j_client):
    """Test filtering assets by tag."""
    # Arrange
    mock_neo4j_client.execute_query.return_value = [...]

    # Act
    response = test_client.get("/api/assets?tag=Environment:production")

    # Assert
    assert response.status_code == 200
    assert len(response.json()) == 5
```

**Step 2: Run test (should fail)**
```bash
pytest tests/test_api.py::test_filter_assets_by_tag
# FAILED - endpoint doesn't exist yet
```

**Step 3: Implement the feature**
```python
# app/main.py
@app.get("/api/assets")
async def get_assets(tag: str | None = None):
    # Implementation
```

**Step 4: Run test (should pass)**
```bash
pytest tests/test_api.py::test_filter_assets_by_tag
# PASSED
```

## Integration with Development Workflow

### Git Workflow

```bash
# 1. Create feature branch
git checkout -b feature/new-collector

# 2. Write tests
# ... edit tests/test_new_collector.py

# 3. Run tests (should fail)
pytest tests/test_new_collector.py

# 4. Implement feature
# ... edit app/collectors/new_collector.py

# 5. Run tests (should pass)
pytest tests/test_new_collector.py

# 6. Run all tests
pytest

# 7. Check coverage
pytest --cov=app

# 8. Commit
git add tests/ app/collectors/
git commit -m "Add new collector with tests"

# 9. Push (CI runs automatically)
git push origin feature/new-collector
```

### CI/CD Pipeline

When you push code:

1. **GitHub Actions runs automatically**
2. **Import tests run first** (fails fast)
3. **Unit tests run** (parallel across Python versions)
4. **Integration tests run** (with real Neo4j/Redis)
5. **Coverage report generated**
6. **Code quality checks** (black, ruff)

If any step fails → Build fails → Can't merge PR

## Debugging Failed Tests

### Test fails locally but not in CI

```bash
# Clear caches
make clean

# Run in same environment as CI
docker compose run --rm backend pytest
```

### Test passes locally but fails in CI

```bash
# Check Python version
python --version

# Run with CI Python version
docker run -it python:3.11-slim bash
pip install -r requirements.txt
pytest
```

### Flaky tests

```bash
# Run test multiple times
pytest tests/test_flaky.py --count=10

# Run with random order
pytest --random-order
```

## Resources

- [Testing Documentation](README.md) in `backend/tests/`
- [Pytest Best Practices](https://docs.pytest.org/en/latest/goodpractices.html)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Test Coverage Guide](https://coverage.readthedocs.io/en/latest/index.html)

## Summary

✅ **Test suite created** with comprehensive coverage
✅ **Import tests** catch module errors before deployment
✅ **API tests** verify endpoints work correctly
✅ **Model tests** validate data structures
✅ **CI/CD pipeline** runs tests automatically
✅ **Coverage reporting** tracks code quality
✅ **Makefile** provides easy commands

**Next time:** Run `make test-imports` before `docker compose up` to catch errors early!
