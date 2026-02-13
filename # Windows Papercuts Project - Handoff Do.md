# Windows Papercuts Project - Handoff Document

## Project Overview

**Project Name:** Windows Papercuts
**Project ID:** `ace21e25-5a3e-4bbd-9126-292512363d50`
**Slug ID:** `ad6768c6e5c2`
**Linear URL:** https://linear.app/arcadedev/project/windows-papercuts-ad6768c6e5c2

**Status:** Started
**Progress:** 16.67% (1 of 6 issues completed)
**Lead:** Francisco
**Start Date:** 2026-02-04
**Target Date:** 2026-02-15

**Teams:**
- Engineering (ENGTOP)
- Tools and DX Engineering (TOO)

## Project Description

A collection of projects to ensure that the Arcade tool-development experience on windows is good.   See the issues for more information.

Then, [Windows Ideal Docs](https://linear.app/arcadedev/project/windows-ideal-docs-423cb7213093/overview) comes

# User Stories

1. The Windows Tool Developer

As a tool developer on Windows, I want a clear setup path and reliable CLI and SDK behavior, so I can build and run tools without platform-specific surprises.

2. The CLI and SDK Maintainer

As a maintainer, I want a Windows-focused CI test suite that exercises real CLI workflows, so regressions are caught before release.

# Engineering Planning

After we learned that around 40% of customers are on Windows, Nate spent time testing the tool-building experience with the Arcade MCP Python SDK on Windows. He confirmed the SDK runs, but found rough corners that would improve the Windows community experience. He logged those rough corners as issues in this project.

This project first aimed to fix Nate's issues and document how to use the Arcade MCP Python SDK on Windows. That scope now splits into two projects. The first focuses on fixing the reported issues and recording the steps to set up and run the SDK on Windows, plus any rough edges found along the way. The second uses those notes to design Windows-focused documentation that makes setup and tool development smoother.

Most issues are straightforward. The one that needs extra attention is designing a Windows test suite for CI that protects the CLI from regressions, and that needs a clear plan before implementation.

Detailed documentation updated and powershell scripts / LLM prompts that help creating the development in windows platform is out of scope for this project but will be scopped for the follow up one.

### Methodology

With the provided Windows VM, I will start from scratch building the environment required to run our CLI and Python SDK on Windows. I will record each setup step and any rough edges I find, especially anything that does not have a direct parallel on Unix environments. I will use Cursor on Windows to make the fixes, so I feel the workflow as a Windows developer working in our codebase.

### Windows test suite in CI

As suggested by Nate, one of the most important items in this project is a solid Windows test suite integrated into CI to catch CLI regressions early.

### Added: Test planning details for Windows CI

* Expand the current install smoke test to run a small set of real CLI commands on Windows, macOS, and Linux without requiring login.
* Add integration tests for `arcade configure` that write to a temp `--config` path and verify the JSON shape for claude, cursor, and vscode, for both stdio and http.
* Add a test for `arcade new` that scaffolds in a temp dir and verifies expected files and directories are created with Windows paths and spaces.
* Add path handling tests for Windows-style paths, backslashes, spaces, and long paths in output file arguments and eval discovery.
* Added: CI shape and scope
* Keep the existing install workflow, but add a dedicated CLI workflow that runs on Windows, macOS, and Ubuntu with Python 3.10.

## Sharing Plan

For sharing, we can update Windows users in the weekly newsletter that the CLI has been improved for their OS. In the second project, we will have a stronger deliverable for sharing: Windows-focused documentation on how to build Arcade tools.

## Measurement Plan

For measurement, we can track how many Windows users are building tools with Arcade using existing CLI telemetry. We can also track Windows-specific CI failure rates and the number of Windows-related support issues before and after the changes.

## Issues

### Completed Issues (1)

#### TOO-325: Ensure that Arcade Employees have access to on-demand windows computers
- **Status:** Done (completed)
- **Priority:** None
- **Updated:** 2026-01-17T01:14:08.802Z
- **URL:** https://linear.app/arcadedev/issue/TOO-325/ensure-that-arcade-employees-have-access-to-on-demand-windows

### Open Issues (5)

#### TOO-326: Ensure a robust test suite for Windows in CI for the CLI and `arcade-mcp`
- **Status:** Todo (unstarted)
- **Priority:** None
- **Updated:** 2026-01-16T19:16:42.476Z
- **URL:** https://linear.app/arcadedev/issue/TOO-326/ensure-a-robust-test-suite-for-windows-in-ci-for-the-cli-and-arcade

#### TOO-327: Improve CLI output spacing in Arcade quickstart
- **Status:** Todo (unstarted)
- **Priority:** High
- **Updated:** 2026-01-16T19:14:24.387Z
- **URL:** https://linear.app/arcadedev/issue/TOO-327/improve-cli-output-spacing-in-arcade-quickstart

#### TOO-324: Address ArcadeMCP Windows signal handling warning text
- **Status:** Todo (unstarted)
- **Priority:** None
- **Updated:** 2026-01-16T19:11:41.180Z
- **URL:** https://linear.app/arcadedev/issue/TOO-324/address-arcademcp-windows-signal-handling-warning-text

#### TOO-323: Suppress ArcadeMCP phantom terminal windows on Windows
- **Status:** Todo (unstarted)
- **Priority:** None
- **Updated:** 2026-01-16T19:11:39.112Z
- **URL:** https://linear.app/arcadedev/issue/TOO-323/suppress-arcademcp-phantom-terminal-windows-on-windows

#### TOO-322: Fix arcade configure cursor Windows path detection
- **Status:** Todo (unstarted)
- **Priority:** None
- **Updated:** 2026-01-16T19:11:37.130Z
- **URL:** https://linear.app/arcadedev/issue/TOO-322/fix-arcade-configure-cursor-windows-path-detection

## Summary

This project focuses on improving the Windows development experience for Arcade tool developers. With 40% of customers on Windows, ensuring a smooth CLI and SDK experience is critical. The project has 6 issues total, with 1 completed and 5 remaining. The highest priority open issue is TOO-327 (Improve CLI output spacing in Arcade quickstart).

The project includes a comprehensive plan for adding Windows CI test coverage and follows a methodology of building from scratch on Windows to identify and fix platform-specific issues.
