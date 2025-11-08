# Backend Tests

Comprehensive test suite for the Asset Inventory backend.

## Test Structure

```
tests/
├── conftest.py              # Pytest fixtures and configuration
├── test_imports.py          # Import sanity checks
├── test_models.py           # Data model tests
├── test_api.py              # API endpoint tests
├── test_collectors.py       # AWS collector tests
└── README.md               # This file
```

## Running Tests

### Quick Start

```bash
# Run all tests
make test

# Run import tests only (quick sanity check)
make test-imports

# Run without coverage (faster)
make test-fast
```

### Detailed Commands

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests with coverage
pytest

# Run specific test file
pytest tests/test_imports.py

# Run specific test
pytest tests/test_api.py::TestHealthEndpoint::test_health_check_healthy

# Run with verbose output
pytest -v

# Run and show print statements
pytest -s

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf
```

## Test Categories

Tests are marked with categories:

- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Tests requiring external services
- `@pytest.mark.slow` - Slow-running tests

Run specific categories:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run everything except slow tests
pytest -m "not slow"
```

## Coverage

```bash
# Generate coverage report
pytest --cov=app --cov-report=html

# Open coverage report in browser
make test-cov
```

Coverage goals:
- **Minimum**: 70%
- **Target**: 85%+
- **Critical paths**: 95%+

## Fixtures

Key test fixtures in `conftest.py`:

- `mock_neo4j_client` - Mocked Neo4j database
- `mock_redis_client` - Mocked Redis client
- `sample_asset` - Sample asset for testing
- `sample_enrichment` - Sample enrichment data
- `sample_config_item` - AWS Config item
- `test_client` - FastAPI test client
- `mock_boto3_session` - Mocked AWS session

## Writing Tests

### Test Naming Convention

```python
class TestFeatureName:
    """Tests for FeatureName."""

    def test_specific_behavior(self):
        """Test that specific behavior works correctly."""
        # Arrange
        ...
        # Act
        ...
        # Assert
        ...
```

### Using Fixtures

```python
def test_with_fixtures(sample_asset, mock_neo4j_client):
    """Test using fixtures."""
    # Fixtures are automatically injected
    assert sample_asset.name == "api-service"
    assert mock_neo4j_client.verify_connectivity() is True
```

### Mocking External Services

```python
from unittest.mock import patch, MagicMock

@patch('boto3.Session')
def test_with_mock(mock_session_class):
    """Test with mocked AWS session."""
    mock_session = MagicMock()
    mock_session_class.return_value = mock_session
    # Your test code
```

## Continuous Integration

Tests run automatically on:
- Every push to `main` or `develop`
- Every pull request
- GitHub Actions workflow: `.github/workflows/backend-tests.yml`

## Test Data

Sample test data should be:
- **Realistic** - Based on actual AWS resource structures
- **Minimal** - Only what's needed for the test
- **Isolated** - Each test should be independent

## Troubleshooting

**Tests fail with import errors:**
```bash
# Check all modules can be imported
pytest tests/test_imports.py -v
```

**Tests fail with database errors:**
```bash
# Ensure Neo4j and Redis are running
docker compose up -d neo4j redis
```

**Coverage is too low:**
```bash
# See which lines aren't covered
pytest --cov=app --cov-report=term-missing
```

**Tests are slow:**
```bash
# Run without coverage
pytest --no-cov

# Or run only fast tests
pytest -m "not slow"
```

## Best Practices

1. **Fast Tests** - Unit tests should run in milliseconds
2. **Isolated Tests** - No dependencies between tests
3. **Clear Assertions** - One logical assertion per test
4. **Descriptive Names** - Test name should describe what it tests
5. **Arrange-Act-Assert** - Structure tests clearly
6. **Mock External Services** - Don't make real AWS API calls
7. **Test Edge Cases** - Not just the happy path

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)
