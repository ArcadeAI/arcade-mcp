# Arcade CLI

Command-line interface for the Arcade platform.

## Overview

Arcade CLI provides a comprehensive command-line interface for the Arcade platform:

- **User Authentication**: Login, logout, and user management
- **Tool Development**: Create, test, and manage Arcade tools
- **Worker Deployment**: Deploy and manage Arcade workers
- **Interactive Chat**: Test tools in an interactive environment
- **Project Templates**: Generate new toolkit projects

## Installation

```bash
pip install arcadecli
```

## Usage

### Authentication

```bash
# Login to Arcade
arcade auth login

# Check authentication status
arcade auth status

# Logout
arcade auth logout
```

### Tool Development

```bash
# Create a new toolkit
arcade new my-toolkit

# Show available tools
arcade show tools

# Show toolkit information
arcade show toolkit my-toolkit
```

### Worker Management

```bash
# Start a worker
arcade worker start

# Deploy a worker
arcade deploy worker

# Show worker status
arcade show workers
```

### Interactive Chat

```bash
# Start interactive chat with tools
arcade chat

# Chat with specific toolkit
arcade chat --toolkit my-toolkit
```

## Dependencies

- `arcade-core>=1.1.0` - Core Arcade functionality
- `arcade-tdk>=1.1.0` - Tool development kit
- `arcade-serve>=1.1.0` - Serving infrastructure
- `arcade-evals>=1.1.0` - Evaluation framework
- `typer>=0.9.0` - CLI framework
- `rich>=13.7.1` - Rich terminal output

## License

MIT License - see LICENSE file for details.
