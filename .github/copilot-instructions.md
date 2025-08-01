# Project Overview

This project is focused on developing an agent that autonomously builds an ontology from a given legal act text.
The full specification and design details can be found in the [documentation/specification.md](documentation/specification.md) file.
The agent will run from the command line only, and it will not have a graphical user interface (GUI).
The agent will be implemented in Python, and it will utilize various libraries for natural language processing and ontology management.
The agent will be designed to be modular, allowing for easy updates and improvements in the future.

# Coding Guidelines

Follow the guidelines outlined in the [documentation/specification.md](documentation/specification.md) file for coding standards and practices.
Whenever you implement something new, based either on the discussion in the chat or on your own research, ensure that you also update the documentation in the specification file [documentation/specification.md](documentation/specification.md) to reflect the changes made.

# Testing Guidelines
We do not use any testing library or tool.
We write tests as simple Python scripts with main functions that can be run directly and print the results to the console.
The tests should be placed directly in the src directory next to the code they are testing.
The tests should be named with a `test_` prefix, and they should be self-contained.
Each test should be able to run independently without requiring any setup or teardown.
Each test should be runnable in the debug mode.