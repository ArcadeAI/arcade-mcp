'use strict'

const PROMISE_STATICS = require('./lib/promise-statics')
const getDocsUrl = require('./lib/get-docs-url')

const PROMISE_INSTANCE_METHODS = new Set(['then', 'catch', 'finally'])

function isPermittedProperty(expression, standardSet, allowedMethods) {
  // istanbul ignore if
  if (expression.type !== 'MemberExpression') return false

  if (expression.property.type === 'Literal')
    return (
      standardSet.has(expression.property.value) ||
      allowedMethods.includes(expression.property.value)
    )

  // istanbul ignore else
  if (expression.property.type === 'Identifier')
    return (
      expression.computed ||
      standardSet.has(expression.property.name) ||
      allowedMethods.includes(expression.property.name)
    )

  // istanbul ignore next
  return false
}

module.exports = {
  meta: {
    type: 'problem',
    docs: {
      description: 'Disallow use of non-standard Promise static methods.',
      url: getDocsUrl('spec-only'),
    },
    schema: [
      {
        type: 'object',
        properties: {
          allowedMethods: {
            type: 'array',
            items: {
              type: 'string',
            },
          },
        },
        additionalProperties: false,
      },
    ],
    messages: {
      avoidNonStandard: "Avoid using non-standard 'Promise.{{ name }}'",
    },
  },
  create(context) {
    const { allowedMethods = [] } = context.options[0] || {}

    return {
      MemberExpression(node) {
        if (
          node.object.type === 'Identifier' &&
          node.object.name === 'Promise' &&
          ((node.property.name !== 'prototype' &&
            !isPermittedProperty(node, PROMISE_STATICS, allowedMethods)) ||
            (node.property.name === 'prototype' &&
              node.parent.type === 'MemberExpression' &&
              !isPermittedProperty(
                node.parent,
                PROMISE_INSTANCE_METHODS,
                allowedMethods,
              )))
        ) {
          context.report({
            node,
            messageId: 'avoidNonStandard',
            data: { name: node.property.name ?? node.property.value },
          })
        }
      },
    }
  },
}
