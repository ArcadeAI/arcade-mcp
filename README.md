[![Release](https://img.shields.io/github/v/release/arcadeai/arcade-ai)](https://img.shields.io/github/v/release/arcadeai/arcade-ai)
[![Build status](https://img.shields.io/github/actions/workflow/status/arcadeai/arcade-ai/main.yml?branch=main)](https://github.com/arcadeai/arcade-ai/actions/workflows/main.yml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/arcadeai/arcade-ai/branch/main/graph/badge.svg)](https://codecov.io/gh/arcadeai/arcade-ai)
[![Commit activity](https://img.shields.io/github/commit-activity/m/arcadeai/arcade-ai)](https://img.shields.io/github/commit-activity/m/arcadeai/arcade-ai)
[![License](https://img.shields.io/github/license/arcadeai/arcade-ai)](https://img.shields.io/github/license/arcadeai/arcade-ai)


# Arcade AI

Arcade AI is the developer platform for building tools designed to be used with language models. With Arcade, developers can create, deploy, and easily integrate new tools with language models to enhance their capabilities.

## `arcade-ai`

The `arcade-ai` package contains:
 - `arcade` CLI
 - `arcade.sdk` Tool SDK
 - `arcade.actor` serving tools with FastAPI, Flask, or Django

## Installation

To install the Arcade AI package, execute the following command:

```bash
pip install arcade-ai
```

or install from source:

```bash
git clone https://github.com/arcadeai/arcade-ai.git
cd arcade-ai
pip install poetry
poetry install
```

## First steps

Follow these steps if you've cloned the repo and installed the package from source:

```bash
cd examples/search
poetry install

arcade show arcade_search
```
This will show an output that looks like

┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┓
┃ Name         ┃ Description                                                    ┃ Toolkit   ┃ Version ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━┩
│ SearchGoogle │ Search Google using SerpAPI and return organic search results. │ search │ 0.1.0   │
└──────────────┴────────────────────────────────────────────────────────────────┴───────────┴─────────┘


Predict the parameters with a model and run the tool with the predicted parameters. Arcade adds the `execute` choice to the tool, which allows you to run the tool with the predicted parameters in a single request.

```bash
> arcade run arcade_search "who is Sam Partee?" --choice "execute"
Running tool: SearchGoogle with params: {'query': 'Sam Partee'}

[{"position": 1, "title": "Sam Partee (@SamPartee) / X", "link": "https://twitter.com/sampartee", "redirect_link":
"https://www.google.com/url?sa=t&source=web&rct=j&opi=89978449&url=https://twitter.com/sampartee&ved=2ahUKEwjBwKiz3b6HAxV1VTABHXL8BZQQFnoECAYQAQ",
"displayed_link": "1.5K+ followers", "thumbnail":
.....
.. (truncated)
```

Arcade also adds the `predict` choice to the tool, which allows you to predict the parameters with a model.

```bash
> arcade run arcade_search "who is Sam Partee?" --choice "predict" # also the default
Running tool: SearchGoogle with params: {'query': 'Sam Partee'}

Sam Partee is a CTO, Co-founder of Arcade AI and former Machine Learning Engineer at companies like RedisInc and HPE_Cray. They have
expertise in AI/ML, vector search, Python, HPC, and are a sports fan.
```
