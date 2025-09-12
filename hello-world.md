# Hello World - Arcade AI Platform 👋

Welcome to the **Arcade AI Platform** repository!

## What is Arcade?

Arcade is a developer platform that lets you build, deploy, and manage tools for AI agents. This repository contains the core Arcade libraries and examples to help you get started building powerful AI tools.

## Quick Hello World Example

Here's a simple "Hello World" tool using Arcade's Tool Development Kit (TDK):

```python
from typing import Annotated
from arcade_tdk import tool

@tool
def hello_world(name: Annotated[str, "The name of the person to greet"]) -> str:
    """Say hello to someone using Arcade AI."""
    return f"Hello, {name}! Welcome to Arcade AI Platform! 🎮"

# The tool is automatically registered and available for use
```

## Repository Structure

This repository is organized into several key packages:

- 🔧 **arcade-core** - Core platform functionality and schemas
- 🛠️ **arcade-tdk** - Tool Development Kit with the `@tool` decorator  
- 🚀 **arcade-serve** - Serving infrastructure for workers and MCP servers
- 📊 **arcade-evals** - Evaluation framework for testing tool performance
- 💻 **arcade-cli** - Command-line interface for the Arcade platform

## Getting Started

1. **Installation**: Install Arcade packages via pip
   ```bash
   pip install arcade-tdk  # For tool development
   pip install arcade-ai   # For CLI access
   ```

2. **Explore Examples**: Check out the `/examples` directory for:
   - LangChain integrations
   - CrewAI examples  
   - OpenAI Agents
   - And more!

3. **Build Tools**: Use the examples in `/toolkits` to see real-world implementations

## Learn More

- 📚 [Documentation](https://docs.arcade.dev/home)
- 🔗 [Available Tools](https://docs.arcade.dev/tools)
- ⚡ [Quickstart Guide](https://docs.arcade.dev/home/quickstart)
- 💬 [Contact Us](https://docs.arcade.dev/home/contact-us)

---

**Happy building with Arcade AI! 🎮✨**

*Give us a ⭐ if you find this project helpful!*