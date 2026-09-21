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

1. Install an arcade toolkit
```bash
pip install arcade-math
```

2. Load the toolkit
```python
import arcade_math
from arcade_core import ToolCatalog, Toolkit

# Create a tool catalog
catalog = ToolCatalog()

# Load a toolkit
toolkit = Toolkit.from_module(arcade_math)
```

## Reserved tool argument names

The top-level exposed input name `connected_account` is reserved for Arcade Engine use. A tool-owned argument with that exposed name would collide with the value the Engine injects for multi-account providers.

Conflicting definitions now fail during definition building or registration with an actionable `ToolInputSchemaError`. Tool authors must rename the exposed input and update callers that send that input. Renaming only the Python parameter while keeping an `Annotated` alias of `connected_account` does not resolve the conflict.

Nested data fields and output fields may still use this name. This reservation does not add account-selection functionality.

### Migration

Before — a tool-owned `connected_account` input:

```python
from typing import Annotated

from arcade_tdk import tool


@tool
def lookup_inbox(connected_account: Annotated[str, "Account to look up"]) -> str:
    """Look up an inbox by account."""
    return connected_account
```

Callers send `{"connected_account": "..."}`.

After — rename the exposed input and update the function body and caller payloads:

```python
from typing import Annotated

from arcade_tdk import tool


@tool
def lookup_inbox(account_reference: Annotated[str, "Account to look up"]) -> str:
    """Look up an inbox by account."""
    return account_reference
```

Callers send `{"account_reference": "..."}`.

The reserved name is the **exposed** input name: the Python parameter name, or the first string in `Annotated[type, "name", "description"]` when an alias is used. Changing only the Python identifier while aliasing `connected_account` still fails.

## License

MIT License - see LICENSE file for details.
