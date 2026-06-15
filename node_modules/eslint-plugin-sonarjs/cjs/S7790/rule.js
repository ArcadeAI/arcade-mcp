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
// https://sonarsource.github.io/rspec/#/rspec/S7790/javascript
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
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const module_js_1 = require("../helpers/module.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
const templatingFqns = new Set([
    'pug.compile',
    'pug.render',
    'ejs.compile',
    'ejs.render',
]);
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            reviewDynamicTemplate: `Make sure this dynamically formatted template is safe here.`,
        },
    }),
    create(context) {
        return {
            CallExpression: (node) => {
                const callExpression = node;
                const fqn = (0, module_js_1.getFullyQualifiedName)(context, callExpression);
                if (fqn &&
                    templatingFqns.has(fqn) &&
                    !isCallingFunctionResult(context, callExpression) &&
                    isQuestionable(callExpression)) {
                    context.report({
                        messageId: 'reviewDynamicTemplate',
                        node: callExpression.callee,
                    });
                }
            },
        };
    },
};
/**
 * Returns true when the callee is a variable holding the result of a prior call,
 * e.g. `const fn = pug.compile(tpl); fn(data);` — fn(data) is not a direct
 * templating call, so we should not flag it again.
 */
function isCallingFunctionResult(context, callExpression) {
    const callee = callExpression.callee;
    if (callee.type !== 'Identifier') {
        return false;
    }
    const variable = (0, ast_js_1.getVariableFromScope)(context.sourceCode.getScope(callee), callee.name);
    if (!variable || variable.defs.some(def => def.type === 'ImportBinding')) {
        return false;
    }
    const writeRef = (0, ast_js_1.getUniqueWriteReference)(variable);
    return writeRef?.type === 'CallExpression';
}
function isQuestionable(node, index = 0) {
    const args = node.arguments;
    const templateString = args[index];
    if (!templateString) {
        return false;
    }
    // Is a template literal with expressions
    if (templateString.type === 'TemplateLiteral' && templateString.expressions.length !== 0) {
        return true;
    }
    // Is a concatenation involving one or more variables
    if (isConcatenation(templateString)) {
        return isVariableConcat(templateString);
    }
    // Is a variable which value cannot be determined statically
    return !isHardcodedLiteral(templateString);
}
function isVariableConcat(node) {
    const { left, right } = node;
    if (!isHardcodedLiteral(right)) {
        return true;
    }
    if (isConcatenation(left)) {
        return isVariableConcat(left);
    }
    return !isHardcodedLiteral(left);
}
function isConcatenation(node) {
    return node.type === 'BinaryExpression' && node.operator === '+';
}
function isHardcodedLiteral(node) {
    // A hardcoded string literal or a template literal without expressions
    return (node.type === 'Literal' || (node.type === 'TemplateLiteral' && node.expressions.length === 0));
}
