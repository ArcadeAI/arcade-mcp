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
// https://sonarsource.github.io/rspec/#/rspec/S2757
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
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            useExistingOperator: 'Was "{{operator}}=" meant instead?',
            suggestExistingOperator: 'Replace with "{{operator}}" operator',
        },
        hasSuggestions: true,
    }),
    create(context) {
        return {
            AssignmentExpression(assignmentExpression) {
                if (assignmentExpression.operator === '=') {
                    checkOperator(context, assignmentExpression.right);
                }
            },
            VariableDeclarator(variableDeclarator) {
                checkOperator(context, variableDeclarator.init);
            },
        };
    },
};
function checkOperator(context, unaryNode) {
    if (unaryNode?.type === 'UnaryExpression' && isUnaryOperatorOfInterest(unaryNode.operator)) {
        const { sourceCode } = context;
        const assignmentOperatorToken = sourceCode.getTokenBefore(unaryNode, token => token.value === '=');
        const unaryOperatorToken = sourceCode.getFirstToken(unaryNode);
        const expressionFirstToken = sourceCode.getFirstToken(unaryNode.argument);
        if (assignmentOperatorToken != null &&
            unaryOperatorToken != null &&
            expressionFirstToken != null &&
            areAdjacent(assignmentOperatorToken, unaryOperatorToken) &&
            !areAdjacent(unaryOperatorToken, expressionFirstToken)) {
            const suggest = [];
            if (unaryNode.parent?.type === 'AssignmentExpression') {
                const range = [
                    assignmentOperatorToken.range[0],
                    unaryOperatorToken.range[1],
                ];
                const invertedOperators = unaryOperatorToken.value + assignmentOperatorToken.value;
                suggest.push({
                    messageId: 'suggestExistingOperator',
                    data: {
                        operator: invertedOperators,
                    },
                    fix: fixer => fixer.replaceTextRange(range, invertedOperators),
                });
            }
            context.report({
                messageId: 'useExistingOperator',
                data: {
                    operator: unaryNode.operator,
                },
                loc: { start: assignmentOperatorToken.loc.start, end: unaryOperatorToken.loc.end },
                suggest,
            });
        }
    }
}
function isUnaryOperatorOfInterest(operator) {
    return operator === '-' || operator === '+' || operator === '!';
}
function areAdjacent(first, second) {
    return (first.loc.end.column === second.loc.start.column && first.loc.end.line === second.loc.start.line);
}
