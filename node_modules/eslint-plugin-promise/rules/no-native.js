// Borrowed from here:
// https://github.com/colonyamerican/eslint-plugin-cah/issues/3

'use strict'

const { getSourceCode } = require('./lib/eslint-compat')
const getDocsUrl = require('./lib/get-docs-url')

function isDeclared(scope, ref) {
  return scope.variables.some((variable) => {
    if (variable.name !== ref.identifier.name) {
      return false
    }

    // Presumably can't pass this since the implicit `Promise` global
    //  being checked here would always lack `defs`
    // istanbul ignore else
    if (!variable.defs || !variable.defs.length) {
      return false
    }

    // istanbul ignore next
    return true
  })
}

module.exports = {
  meta: {
    type: 'suggestion',
    docs: {
      description:
        'Require creating a `Promise` constructor before using it in an ES5 environment.',
      url: getDocsUrl('no-native'),
    },
    messages: {
      name: '"{{name}}" is not defined.',
    },
    schema: [],
  },
  create(context) {
    /**
     * Checks for and reports reassigned constants
     *
     * @param {Scope} scope - an eslint-scope Scope object
     * @returns {void}
     * @private
     */
    return {
      'Program:exit'() {
        const sourceCode = getSourceCode(context)
        /** @type {import('eslint').Scope.Scope} */
        const scope = sourceCode.scopeManager.globalScope

        for (const variable of scope.variables) {
          if (variable.name !== 'Promise') {
            continue
          }
          variable.references.forEach(validatePromiseReference)
        }
        for (const ref of scope.through) {
          if (ref.identifier.name !== 'Promise') {
            continue
          }
          validatePromiseReference(ref)
        }
        function validatePromiseReference(ref) {
          // istanbul ignore else
          if (!isDeclared(scope, ref)) {
            context.report({
              node: ref.identifier,
              messageId: 'name',
              data: { name: ref.identifier.name },
            })
          }
        }
      },
    }
  },
}
