<h3 align="center">
  <a name="readme-top"></a>
  <img
    src="https://docs.arcade.dev/images/logo/arcade-logo.png"
    style="width: 400px;"
  >
</h3>
<div align="center">
    <a href="https://github.com/arcadeai/arcade-ai/blob/main/LICENSE">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</a>
  <img src="https://img.shields.io/github/last-commit/ArcadeAI/arcade-ai" alt="GitHub last commit">
<a href="https://github.com/arcadeai/arcade-ai/actions?query=branch%3Amain">
<img src="https://img.shields.io/github/actions/workflow/status/arcadeai/arcade-ai/main.yml?branch=main" alt="GitHub Actions Status">
</a>
<a href="https://img.shields.io/pypi/pyversions/arcade-ai">
  <img src="https://img.shields.io/pypi/pyversions/arcade-ai" alt="Python Version">
</a>
</div>
<div>
  <p align="center" style="display: flex; justify-content: center; gap: 10px;">
    <a href="https://x.com/TryArcade">
      <img src="https://img.shields.io/badge/Follow%20on%20X-000000?style=for-the-badge&logo=x&logoColor=white" alt="Follow on X" style="width: 125px;height: 25px; padding-top: .8px; border-radius: 5px;" />
    </a>
    <a href="https://www.linkedin.com/company/arcade-ai" >
      <img src="https://img.shields.io/badge/Follow%20on%20LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white" alt="Follow on LinkedIn" style="width: 150px; padding-top: 1.5px;height: 22px; border-radius: 5px;" />
    </a>
    <a href="https://discord.com/invite/GUZEMpEZ9p">
      <img src="https://img.shields.io/badge/Join%20our%20Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Join our Discord" style="width: 150px; padding-top: 1.5px; height: 22px; border-radius: 5px;" />
    </a>
  </p>
</div>

<p align="center" style="display: flex; justify-content: center; gap: 5px; font-size: 15px;">
    <a href="https://docs.arcade.dev/home" target="_blank">Documentation</a> •
    <a href="https://docs.arcade.dev/tools" target="_blank">Tools</a> •
    <a href="https://docs.arcade.dev/home/quickstart" target="_blank">Quickstart</a> •
    <a href="https://docs.arcade.dev/home/contact-us" target="_blank">Contact Us</a>

# Arcade AI Platform

Arcade is a developer platform that lets you build, deploy, and manage tools for AI agents.

This repository contains the core Arcade libraries, organized as separate packages for maximum flexibility and modularity:

-   **arcade-core** - Core platform functionality and schemas | [Source code](https://github.com/ArcadeAI/arcade-ai/tree/main/libs/arcade-core) | `pip install arcade-core` |
-   **arcade-tdk** - Tool Development Kit with the `@tool` decorator | [Source code](https://github.com/ArcadeAI/arcade-ai/tree/main/libs/arcade-tdk) | `pip install arcade-tdk` |
-   **arcade-serve** - Serving infrastructure for workers and MCP servers | [Source code](https://github.com/ArcadeAI/arcade-ai/tree/main/libs/arcade-serve) | `pip install arcade-serve` |
-   **arcade-evals** - Evaluation framework for testing tool performance | [Source code](https://github.com/ArcadeAI/arcade-ai/tree/main/libs/arcade-evals) | `pip install 'arcade-ai[evals]` |
-   **arcade-cli** - Command-line interface for the Arcade platform | [Source code](https://github.com/ArcadeAI/arcade-ai/tree/main/libs/arcade-cli) | `pip install arcade-ai` |

![diagram](https://github.com/user-attachments/assets/1a567e5f-d6b4-4b1e-9918-c401ad232ebb)

**To learn more about Arcade.dev, check out our [documentation](https://docs.arcade.dev/home).**

_Pst. hey, you, give us a star if you like it!_

<a href="https://github.com/ArcadeAI/arcade-ai">
  <img src="https://img.shields.io/github/stars/ArcadeAI/arcade-ai.svg" alt="GitHub stars">
</a>

## Quick Start

### Installation

For development, install all packages with dependencies using uv workspace:

```bash
# Install all packages and dev dependencies
uv sync --extra all --dev

# Or use the Makefile (includes pre-commit hooks)
make install
```

For production use, install individual packages as needed:

```bash
pip install arcade-ai          # CLI
pip install 'arcade-ai[evals]' # CLI + Evaluation framework
pip install 'arcade-ai[all]'   # CLI + Serving infra + eval framework + TDK
pip install arcade_serve       # Serving infrastructure
pip install arcade-tdk         # Tool Development Kit
```

### Development

Use the Makefile for standard tasks:

```bash
# Run tests
make test

# Run linting and type checking
make check

# Build all packages
make build

# See all available commands
make help
```

## Client Libraries

-   **[ArcadeAI/arcade-py](https://github.com/ArcadeAI/arcade-py):**
    The Python client for interacting with Arcade.

-   **[ArcadeAI/arcade-js](https://github.com/ArcadeAI/arcade-js):**
    The JavaScript client for interacting with Arcade.

-   **[ArcadeAI/arcade-go](https://github.com/ArcadeAI/arcade-go):**
    The Go client for interacting with Arcade.

## Support and Community

-   **Discord:** Join our [Discord community](https://discord.com/invite/GUZEMpEZ9p) for real-time support and discussions.
-   **GitHub:** Contribute or report issues on the [Arcade GitHub repository](https://github.com/ArcadeAI/arcade-ai).
-   **Documentation:** Find in-depth guides and API references at [Arcade Documentation](https://docs.arcade.dev).
