# Contributing to getademo

Thank you for your interest in contributing to getademo! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributors of all skill levels.

## How to Contribute

### Reporting Issues

Before opening an issue:
1. Search existing issues to avoid duplicates
2. Use the issue templates when available
3. Provide as much detail as possible

When reporting bugs, include:
- Operating system and version
- Python version
- ffmpeg version
- Steps to reproduce
- Expected vs actual behavior
- Error messages and logs

### Feature Requests

We welcome feature requests! Please:
1. Check existing issues and discussions first
2. Clearly describe the use case
3. Explain why this feature would be valuable

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```
3. **Make your changes** following the code style guidelines
4. **Add tests** for new functionality
5. **Run tests** to ensure nothing is broken:
   ```bash
   pytest
   ```
6. **Run linting**:
   ```bash
   ruff check src/
   ruff format src/
   ```
7. **Update documentation** if needed
8. **Submit a pull request** with a clear description

## Development Setup

### Prerequisites

- Python 3.10+
- ffmpeg
- Git

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/getademo.git
cd getademo

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install in development mode with all dependencies
pip install -e ".[all,dev]"
```

### Project Structure

```
getademo/
├── src/
│   └── getademo/
│       ├── __init__.py     # Package metadata
│       ├── server.py       # MCP server implementation
│       └── protocol.py     # Demo recording protocol document
├── docs/
│   ├── getting-started.md  # Quick start guide
│   └── tools-reference.md  # Tool API documentation
├── tests/
│   └── test_server.py      # Test suite
├── pyproject.toml          # Project configuration
├── README.md               # Main documentation
├── CONTRIBUTING.md         # This file
├── CHANGELOG.md            # Version history
└── LICENSE                 # MIT license
```

## Code Style Guidelines

### Python

- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Maximum line length: 100 characters
- Use descriptive variable and function names

### Docstrings

Use Google-style docstrings:

```python
def example_function(param1: str, param2: int) -> bool:
    """Short description of the function.
    
    Longer description if needed.
    
    Args:
        param1: Description of param1.
        param2: Description of param2.
    
    Returns:
        Description of return value.
    
    Raises:
        ValueError: When param1 is empty.
    """
    pass
```

### MCP Tool Definitions

When adding new tools:
1. Add the tool definition in `list_tools()`
2. Implement the handler function
3. Add the handler to the `call_tool()` dispatcher
4. Update the protocol document if relevant
5. Add tests
6. Update documentation

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=getademo

# Run specific test file
pytest tests/test_server.py

# Run specific test
pytest tests/test_server.py::test_function_name
```

### Writing Tests

- Place tests in the `tests/` directory
- Use `pytest` and `pytest-asyncio` for async tests
- Mock external dependencies (ffmpeg, OpenAI API)
- Test both success and error cases

## Documentation

### Updating Documentation

- Keep README.md up to date with new features
- Update tools-reference.md when adding/modifying tools
- Add examples for new functionality
- Update CHANGELOG.md with your changes

### Documentation Style

- Use clear, concise language
- Include code examples
- Add troubleshooting sections for common issues

## Release Process

Releases are managed by maintainers. To request a release:
1. Ensure all tests pass
2. Update CHANGELOG.md
3. Open a pull request with version bump

## Getting Help

- Open an issue for bugs or feature requests
- Start a discussion for questions
- Check existing issues and discussions first

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to getademo!


