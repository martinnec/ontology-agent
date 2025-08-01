# Project Overview

This project is focused on developing an agent that autonomously builds an ontology from a given legal act text.
The full specification and design details can be found in the [documentation/specification.md](documentation/specification.md) file.
The agent will run from the command line only, and it will not have a graphical user interface (GUI).
The agent will be implemented in Python, and it will utilize various libraries for natural language processing and ontology management.
The agent will be designed to be modular, allowing for easy updates and improvements in the future.

# Coding Guidelines

Follow the guidelines outlined in the [documentation/specification.md](documentation/specification.md) file for coding standards and practices.
Whenever you implement something new, based either on the discussion in the chat or on your own research, ensure that you also update the documentation in the specification file [documentation/specification.md](documentation/specification.md) to reflect the changes made.
The project uses LLM API for some functionalities. It is always OPENAI API for which you need to set the `OPENAI_API_KEY` environment variable.

# Testing Guidelines

We do not use any testing library or tool.
We write tests as simple Python scripts with main functions that can be run directly and print the results to the console.

## Test File Structure and Naming
- The tests should be placed directly in the src directory next to the code they are testing.
- The tests should be named with a `test_` prefix (e.g., `test_service.py` for testing `service.py`).
- Each test should be self-contained and runnable independently without requiring any setup or teardown.
- Each test should be runnable in debug mode.

## Test File Template
Each test file should follow this structure:

```python
"""
Simple test for the [ModuleName].
This test file follows the project's testing guidelines:
- No testing library dependencies
- Simple Python script with main function
- Tests placed directly in src directory
- Named with test_ prefix
- Self-contained and runnable independently

HOW TO RUN:
From the src directory, run:
    python -m [package].[test_filename]

Or from the project root:
    cd src && python -m [package].[test_filename]

The test uses mock implementations to avoid external dependencies.
"""

import os
# Set any required environment variables for testing
os.environ["REQUIRED_ENV_VAR"] = "dummy-value-for-testing"

# Import statements using relative imports
from .module_to_test import ClassToTest
from .dependencies import Dependencies

class Mock[DependencyName]:
    """Mock implementation of [DependencyName] for testing."""
    # Implement mock methods as needed

def test_[specific_functionality]():
    """Test [specific functionality description]."""
    print("Testing [functionality description]...")
    
    # Test implementation
    # Use assert statements for validation
    
    print("✓ [Functionality] working correctly")

def run_all_tests():
    """Run all test functions."""
    print("=" * 50)
    print("Running [ModuleName] Tests")
    print("=" * 50)
    
    test_functions = [
        test_function1,
        test_function2,
        # ... more test functions
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} FAILED: {e}")
            failed += 1
    
    print("=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 50)
    
    return failed == 0

def main():
    """Main function to run the tests."""
    success = run_all_tests()
    if success:
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed!")
        return 1

if __name__ == "__main__":
    exit(main())
```

## Test Implementation Best Practices

1. **Mock External Dependencies**: Use mock classes to avoid external dependencies like APIs, databases, or file systems.
2. **Clear Test Names**: Name test functions descriptively (e.g., `test_get_legal_act_with_summarization`).
3. **Console Output**: Each test should print what it's testing and confirm success with checkmark (✓) or failure (✗).
4. **Environment Variables**: Set dummy environment variables at the top of the test file to avoid external configuration requirements.
5. **Relative Imports**: Use relative imports (e.g., `from .service import LegislationService`) to ensure tests work when run as modules.
6. **Comprehensive Coverage**: Test both successful operations and edge cases.
7. **Independent Tests**: Each test function should be independent and not rely on state from other tests.

## Running Tests

Tests should be run as Python modules from the src directory:
```bash
cd src
python -m [package].test_[module]
```

Example:
```bash
cd src
python -m legislation.test_service
```

## Test Output Format

Tests should produce clear, formatted output showing:
- What is being tested
- Success/failure status for each test
- Summary of total passed/failed tests
- Clear visual separation using separator lines