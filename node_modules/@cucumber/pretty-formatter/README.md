<h1 align="center">
  <img alt="" width="75" src="https://github.com/cucumber.png"/>
  <br>
  pretty-formatter
</h1>
<p align="center">
  <b>Rich formatting of Cucumber progress and results for the terminal</b>
</p>

<p align="center">
  <a href="https://www.npmjs.com/package/@cucumber/pretty-formatter" style="text-decoration: none"><img src="https://img.shields.io/npm/v/@cucumber/pretty-formatter?style=flat&color=dark-green" alt="Latest version on npm"></a>
  <a href="https://github.com/cucumber/pretty-formatter/actions" style="text-decoration: none"><img src="https://github.com/cucumber/pretty-formatter/actions/workflows/test-javascript.yaml/badge.svg" alt="Build status"></a>
</p>

![Example output of the pretty formatting, showing the different colors used](../screenshots/all-statuses.cucumber.pretty.png)

## Usage

This package is used internally in `@cucumber/cucumber` to provide the `summary`, `progress` and `pretty` formatters; you don't need to install or manage it yourself.
For usage, see https://github.com/cucumber/cucumber-js/blob/main/docs/formatters.md.

You can use these low-level classes to provide formatting for a different implementation of Cucumber.

### SummaryPrinter

Prints a summary of test results including non-passing scenarios, statistics, and snippets.

```typescript
import { SummaryPrinter } from '@cucumber/pretty-formatter'

const printer = new SummaryPrinter()

// each time a message is emitted
printer.update(envelope)
```

Can also be used to summarise a test run that already happened, with a pre-populated `Query` object:

```typescript
import { Query } from '@cucumber/query'
import { SummaryPrinter } from '@cucumber/pretty-formatter'

const query = new Query()

// each time a message is emitted
query.update(envelope)

// later
SummaryPrinter.summarise(query)
```

### ProgressPrinter

Prints test progress as single-character status indicators.

```typescript
import { ProgressPrinter } from '@cucumber/pretty-formatter'

const printer = new ProgressPrinter()

// each time a message is emitted
printer.update(envelope)
```

### PrettyPrinter

Prints test progress in a prettified Gherkin-style format.

```typescript
import { PrettyPrinter } from '@cucumber/pretty-formatter'

const printer = new PrettyPrinter()

// each time a message is emitted
printer.update(envelope)
```

### Themes

Here's the schema for a theme:

```ts
interface Theme {
    attachment?: Style
    dataTable?: {
        all?: Style
        border?: Style
        content?: Style
    }
    docString?: {
        all?: Style
        content?: Style
        delimiter?: Style
        mediaType?: Style
    }
    feature?: {
        all?: Style
        keyword?: Style
        name?: Style
    }
    location?: Style
    rule?: {
        all?: Style
        keyword?: Style
        name?: Style
    }
    scenario?: {
        all?: Style
        keyword?: Style
        name?: Style
    }
    status?: {
        all?: Partial<Record<TestStepResultStatus, Style>>
        icon?: Partial<Record<TestStepResultStatus, string>>
        progress?: Partial<Record<TestStepResultStatus, string>>
    }
    step?: {
        argument?: Style
        keyword?: Style
        text?: Style
    }
    tag?: Style
    symbol?: {
        bullet?: string
    }
}

enum TestStepResultStatus {
    UNKNOWN = "UNKNOWN",
    PASSED = "PASSED",
    SKIPPED = "SKIPPED",
    PENDING = "PENDING",
    UNDEFINED = "UNDEFINED",
    AMBIGUOUS = "AMBIGUOUS",
    FAILED = "FAILED"
}
```

`Style` is any [Node.js supported modifier](https://nodejs.org/api/util.html#modifiers) or an array of them.

See the [default theme](./src/theme.ts) for a good example. It's exported as `CUCUMBER_THEME`, so you can clone and extend it if you'd like.