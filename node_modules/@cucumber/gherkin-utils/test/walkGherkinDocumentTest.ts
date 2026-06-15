import assert from 'assert'

import { GherkinDocumentHandlers, walkGherkinDocument } from '../src'
import parse from './parse'

describe('walkGherkinDocument', () => {
  it('traverses depth first', () => {
    const gherkinDocument = parse(`
      #1
      @A
      Feature: B
        #2
        Background: C

        #3
        @D
        Scenario: E
          #4
          Given F

        Scenario: G
          Given H

        #5
        Rule: I
          @J
          Scenario: K
            Given L
              | M | N |
              | O | P |

            #6
            Examples: Q

          Scenario: R
            Given S
              """
              T
              """

            Examples: U
              | V |
              | W |
`)

    const handlers: GherkinDocumentHandlers<string[]> = {
      comment: (comment, acc) => acc.concat(comment.text.trim()),
      dataTable: (dataTable, acc) => acc,
      docString: (docString, acc) => acc.concat(docString.content),
      tableCell: (tableCell, acc) => acc.concat(tableCell.value),
      tableRow: (tableRow, acc) => acc,
      tag: (tag, acc) => acc.concat(tag.name.substring(1)),
      feature: (feature, acc) => acc.concat(feature.name),
      background: (background, acc) => acc.concat(background.name),
      rule: (rule, acc) => acc.concat(rule.name),
      scenario: (scenario, acc) => acc.concat(scenario.name),
      examples: (examples, acc) => acc.concat(examples.name),
      step: (step, acc) => acc.concat(step.text),
    }

    const names = walkGherkinDocument<string[]>(gherkinDocument, [], handlers)
    assert.deepEqual(names, '#1 A B #2 C #3 D E #4 F G H #5 I J K L M N O P #6 Q R S T U V W'.split(' '))
  })
})
