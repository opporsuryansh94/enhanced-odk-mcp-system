# ODK MCP System Tests

This directory contains tests for the ODK MCP System.

## Test Structure

- `unit/`: Unit tests for individual components
- `integration/`: Integration tests for component interactions
- `e2e/`: End-to-end tests for complete workflows

## Running Tests

To run all tests:

```bash
cd /path/to/odk_mcp_system
python -m pytest tests/
```

To run specific test categories:

```bash
# Run unit tests
python -m pytest tests/unit/

# Run integration tests
python -m pytest tests/integration/

# Run end-to-end tests
python -m pytest tests/e2e/
```

## Test Coverage

To generate a test coverage report:

```bash
cd /path/to/odk_mcp_system
python -m pytest --cov=mcps --cov=agents --cov=ui tests/
```

## Test Configuration

Test configuration is stored in `tests/conftest.py`. This includes fixtures and configuration for all tests.

## Adding New Tests

When adding new tests, follow these guidelines:

1. Place unit tests in the appropriate module directory under `tests/unit/`
2. Place integration tests in the appropriate directory under `tests/integration/`
3. Place end-to-end tests in the appropriate directory under `tests/e2e/`
4. Use descriptive test names that clearly indicate what is being tested
5. Use fixtures from `conftest.py` where appropriate
6. Include docstrings that describe the purpose of the test

