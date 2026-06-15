"use strict";
/*
 * SonarQube JavaScript Plugin
 * Copyright (C) SonarSource Sàrl
 * mailto:info AT sonarsource DOT com
 *
 * You can redistribute and/or modify this program under the terms of
 * the Sonar Source-Available License Version 1, as published by SonarSource Sàrl.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the Sonar Source-Available License for more details.
 *
 * You should have received a copy of the Sonar Source-Available License
 * along with this program; if not, see https://sonarsource.com/license/ssal/
 */
// https://sonarsource.github.io/rspec/#/rspec/S1172/javascript
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.rule = void 0;
exports.isParameterProperty = isParameterProperty;
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        hasSuggestions: true,
        messages: {
            removeOrRenameParameter: 'Remove the unused function parameter "{{param}}" or rename it to "_{{param}}" to make intention explicit.',
            suggestRemoveParameter: 'Remove "{{param}}" (beware of call sites)',
            suggestRenameParameter: 'Rename "{{param}}" to "_{{param}}"',
        },
    }),
    create(context) {
        return {
            'FunctionDeclaration, FunctionExpression'(node) {
                reportUnusedArgument(node, node.id, context);
            },
            ArrowFunctionExpression: (node) => {
                reportUnusedArgument(node, undefined, context);
            },
        };
    },
};
function reportUnusedArgument(node, functionId, context) {
    const parent = node.parent;
    if (parent?.type === 'Property' && parent.kind === 'set') {
        return;
    }
    if (context.sourceCode
        .getScope(node)
        .variables.some(v => v.name === 'arguments' && v.identifiers.length === 0 && v.references.length > 0)) {
        return;
    }
    let parametersVariable = context.sourceCode.getDeclaredVariables(node);
    if (functionId) {
        parametersVariable = parametersVariable.filter(v => v.name !== functionId.name);
    }
    for (const param of parametersVariable) {
        if (isUnusedVariable(param) &&
            !isIgnoredParameter(param) &&
            !isParameterProperty(param) &&
            !isThisParameter(param)) {
            context.report({
                messageId: 'removeOrRenameParameter',
                node: param.identifiers[0],
                data: {
                    param: param.name,
                },
                suggest: getSuggestions(param, context),
            });
        }
    }
}
function getSuggestions(paramVariable, context) {
    const paramIdentifier = paramVariable.identifiers[0];
    const suggestions = [
        {
            messageId: 'suggestRenameParameter',
            data: {
                param: paramVariable.name,
            },
            fix: fixer => fixer.insertTextBefore(paramIdentifier, '_'),
        },
    ];
    const func = paramVariable.defs[0].node;
    if (paramIdentifier.parent === func) {
        suggestions.push(getParameterRemovalSuggestion(func, paramVariable, paramIdentifier, context));
    }
    return suggestions;
}
function getParameterRemovalSuggestion(func, paramVariable, paramIdentifier, context) {
    return {
        messageId: 'suggestRemoveParameter',
        data: {
            param: paramVariable.name,
        },
        fix: fixer => {
            const paramIndex = func.params.indexOf(paramIdentifier);
            const param = func.params[paramIndex];
            if (func.params.length === 1) {
                const openingParenthesis = context.sourceCode.getTokenBefore(param);
                const closingParenthesis = context.sourceCode.getTokenAfter(param, token => token.value === ')');
                let [start, end] = param.range;
                if (openingParenthesis?.value === '(') {
                    start = openingParenthesis.range[0];
                    end = closingParenthesis.range[1];
                }
                return fixer.replaceTextRange([start, end], '()');
            }
            else if (func.params.length - 1 === paramIndex) {
                const commaAfter = context.sourceCode.getTokenAfter(param, token => token.value === ',');
                const commaBefore = context.sourceCode.getTokenBefore(param, token => token.value === ',');
                let start = commaBefore.range[1];
                let end = param.range[1];
                if (commaAfter) {
                    end = commaAfter.range[1];
                }
                else {
                    start = commaBefore.range[0];
                }
                return fixer.removeRange([start, end]);
            }
            else {
                const [start] = func.params[paramIndex].range;
                const [end] = func.params[paramIndex + 1].range;
                return fixer.removeRange([start, end]);
            }
        },
    };
}
function isUnusedVariable(variable) {
    const refs = variable.references;
    //Parameter with default value has one reference, but should still be considered as unused.
    return refs.length === 0 || (refs.length === 1 && refs[0].init);
}
function isIgnoredParameter(variable) {
    return variable.name.startsWith('_');
}
function isParameterProperty(variable) {
    return variable.defs.some(def => {
        const parent = def.name.parent;
        return (parent?.type === 'TSParameterProperty' ||
            (parent?.type === 'AssignmentPattern' && parent.parent?.type === 'TSParameterProperty'));
    });
}
function isThisParameter(variable) {
    return variable.name === 'this';
}
