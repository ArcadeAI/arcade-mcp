# Cucumber Tag Expressions for JavaScript

[The docs are here](https://cucumber.io/docs/cucumber/api/#tag-expressions).

## Usage

```typescript
import { type Node, parse } from '@cucumber/tag-expressions'

const expressionNode: Node = parse('@tagA and @tagB')

expressionNode.evaluate(['@tagA', '@tagB']) // => true
expressionNode.evaluate(['@tagA', '@tagC']) // => false
```