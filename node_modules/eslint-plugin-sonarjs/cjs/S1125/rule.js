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
// https://sonarsource.github.io/rspec/#/rspec/S1125
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
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        hasSuggestions: true,
        messages: {
            removeUnnecessaryBoolean: 'Refactor the code to avoid using this boolean literal.',
            suggestRemoveUnnecessaryBoolean: 'Remove the unnecessary boolean literal',
        },
    }),
    create(context) {
        return {
            BinaryExpression(expression) {
                if (expression.operator === '==' || expression.operator === '!=') {
                    checkBinaryExpression(expression);
                }
            },
            LogicalExpression(expression) {
                checkLogicalExpression(expression);
            },
            UnaryExpression(unaryExpression) {
                if (unaryExpression.operator === '!') {
                    checkUnaryExpression(unaryExpression);
                }
            },
        };
        function checkBinaryExpression(expression) {
            const { left, right, operator } = expression;
            if ((0, ast_js_1.isBooleanLiteral)(left)) {
                reportWithFix(left, fixer => getBinaryFix(fixer, expression, left, right, operator));
            }
            if ((0, ast_js_1.isBooleanLiteral)(right)) {
                reportWithFix(right, fixer => getBinaryFix(fixer, expression, right, left, operator));
            }
        }
        function getBinaryFix(fixer, expression, booleanLiteral, otherOperand, operator) {
            const booleanValue = booleanLiteral.value;
            const otherText = context.sourceCode.getText(otherOperand);
            // x == true -> x, x == false -> !x, x != true -> !x, x != false -> x
            const shouldNegate = (operator === '==' && !booleanValue) || (operator === '!=' && booleanValue);
            const replacement = shouldNegate ? `!${otherText}` : otherText;
            return fixer.replaceText(expression, replacement);
        }
        function checkLogicalExpression(expression) {
            const { left, right, operator } = expression;
            if ((0, ast_js_1.isBooleanLiteral)(left)) {
                reportWithFix(left, fixer => getLogicalFix(fixer, expression, left, right, operator));
            }
            if (operator === '&&' && (0, ast_js_1.isBooleanLiteral)(right)) {
                reportWithFix(right, fixer => getLogicalFix(fixer, expression, right, left, operator));
            }
            // ignore `x || true` and `x || false` expressions outside of conditional expressions and `if` statements
            const parent = expression.parent;
            if (operator === '||' &&
                (0, ast_js_1.isBooleanLiteral)(right) &&
                ((parent.type === 'ConditionalExpression' && parent.test === expression) ||
                    parent.type === 'IfStatement')) {
                reportWithFix(right, fixer => getLogicalFix(fixer, expression, right, left, operator));
            }
        }
        function getLogicalFix(fixer, expression, booleanLiteral, otherOperand, operator) {
            const booleanValue = booleanLiteral.value;
            const otherText = context.sourceCode.getText(otherOperand);
            let replacement;
            if (operator === '&&') {
                // true && x -> x, false && x -> false, x && true -> x, x && false -> false
                replacement = booleanValue ? otherText : 'false';
            }
            else {
                // || operator
                // true || x -> true, false || x -> x, x || true -> true, x || false -> x
                replacement = booleanValue ? 'true' : otherText;
            }
            return fixer.replaceText(expression, replacement);
        }
        function checkUnaryExpression(unaryExpression) {
            const { argument } = unaryExpression;
            if ((0, ast_js_1.isBooleanLiteral)(argument)) {
                reportWithFix(argument, fixer => {
                    const booleanValue = argument.value;
                    const replacement = booleanValue ? 'false' : 'true';
                    return fixer.replaceText(unaryExpression, replacement);
                });
            }
        }
        function reportWithFix(node, fix) {
            context.report({
                messageId: 'removeUnnecessaryBoolean',
                node,
                suggest: [
                    {
                        messageId: 'suggestRemoveUnnecessaryBoolean',
                        fix,
                    },
                ],
            });
        }
    },
};
