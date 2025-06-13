# Contributing to `arcade-ai`

Contributions are welcome, and they are greatly appreciated!
Every little bit helps, and credit will always be given.

You can contribute in many ways:

# Types of Contributions

## Report Bugs

Report bugs at https://github.com/ArcadeAI/arcade-ai/issues

If you are reporting a bug, please include:

-   Your operating system name and version.
-   Any details about your local setup that might be helpful in troubleshooting.
-   Detailed steps to reproduce the bug.

## Fix Bugs

Look through the GitHub issues for bugs.
Anything tagged with "bug" and "help wanted" is open to whoever wants to implement a fix for it.

## Implement Features

Look through the GitHub issues for features.
Anything tagged with "enhancement" and "help wanted" is open to whoever wants to implement it.

## Write Documentation

Arcade could always use more documentation, whether as part of the official docs, in docstrings, or even on the web in blog posts, articles, and such.

## Submit Feedback

The best way to send feedback is to file an issue at https://github.com/ArcadeAI/arcade-ai/issues.

If you are proposing a new feature:

-   Explain in detail how it would work.
-   Keep the scope as narrow as possible, to make it easier to implement.
-   Remember that this is a volunteer-driven project, and that contributions
    are welcome :)

# Get Started!

Ready to contribute? Here's how to set up `arcade-ai` for local development.
Please note this documentation assumes you already have `uv` and `Git` installed and ready to go.

1. Fork the `arcade-ai` repo on GitHub.

2. Clone your fork locally:

```bash
cd <directory_in_which_repo_should_be_created>
git clone git@github.com:YOUR_GITHUB_USERNAME/arcade-ai.git
```

3. Now we need to install the environment. Navigate into the directory

```bash
cd arcade-ai
```

Create your virtual environment

```bash
uv venv --python 3.11.6
```

4. Install the development environment and dependencies:

```bash
# Install all packages and development dependencies via uv workspace
uv sync --extra all --dev

# Install pre-commit hooks for code quality
uv run pre-commit install
```

Or use the convenient Makefile command that does both:

```bash
make install
```

The uv workspace will automatically handle installing all lib packages in the correct dependency order.

5. Create a branch for local development:

```bash
git checkout -b name-of-your-bugfix-or-feature
```

Now you can make your changes locally.

6. Don't forget to add test cases for your added functionality to the `libs/tests` directory.

7. When you're done making changes, check that your changes pass the formatting tests.

```bash
make check
```

Now, validate that all unit tests are passing:

```bash
make test
```

8. You can also run tests for specific components:

```bash
# Test all lib packages
make test
```

9. The CI/CD pipeline will run additional checks across different Python versions, so local testing with a single version is usually sufficient.

10. Commit your changes and push your branch to GitHub:

```bash
git add .
git commit -m "Your detailed description of your changes."
git push origin name-of-your-bugfix-or-feature
```

11. Submit a pull request through the GitHub website.

# Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.

2. If the pull request adds functionality, the [docs](https://github.com/ArcadeAI/docs) should be updated.

3. If making contributions to multiple toolkits (i.e. Google and Slack, etc.), submit a separate pull request for each.
   This helps us segregate the changes during the review process making it more efficient.
