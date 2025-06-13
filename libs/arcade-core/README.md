# Arcade Core

Core library for the Arcade platform providing foundational components and utilities.

## Overview

Arcade Core provides the essential building blocks for the Arcade platform:

- **Tool Catalog & Toolkit Management**: Core classes for managing and organizing tools
- **Configuration & Schema Handling**: Configuration management and validation
- **Authentication & Authorization**: Auth providers and security utilities
- **Error Handling**: Comprehensive error types and handling
- **Telemetry & Observability**: Monitoring and tracing capabilities
- **Utilities**: Common helper functions and validators

## Installation

```bash
pip install arcade-core
```

## Usage

```python
from arcade_core import ToolCatalog, Toolkit, ArcadeConfig

# Create a tool catalog
catalog = ToolCatalog()

# Load a toolkit
toolkit = Toolkit.from_directory("path/to/toolkit")

# Configure Arcade
config = ArcadeConfig.from_file("config.yaml")
```

## License

MIT License - see LICENSE file for details.
