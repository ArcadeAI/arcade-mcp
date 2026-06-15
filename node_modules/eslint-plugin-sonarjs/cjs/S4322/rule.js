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
// https://sonarsource.github.io/rspec/#/rspec/S4322/javascript
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
const location_js_1 = require("../helpers/location.js");
const ancestor_js_1 = require("../helpers/ancestor.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        hasSuggestions: true,
        messages: {
            useTypePredicate: 'Declare this function return type using type predicate "{{castedExpressionText}} is {{castedTypeText}}".',
            suggestTypePredicate: 'Use type predicate',
        },
    }),
    create(context) {
        return {
            "MethodDefinition[kind='method'] FunctionExpression"(node) {
                checkFunctionLikeDeclaration(node, context);
            },
            FunctionDeclaration(node) {
                checkFunctionLikeDeclaration(node, context);
            },
        };
    },
};
function checkFunctionLikeDeclaration(functionDeclaration, context) {
    if (functionDeclaration.returnType?.typeAnnotation.type === 'TSTypePredicate') {
        return;
    }
    const body = functionDeclaration.body;
    const returnedExpression = getReturnedExpression(body);
    if (!returnedExpression) {
        return;
    }
    if (isInequalityBinaryExpression(returnedExpression)) {
        const { left, right } = returnedExpression;
        if ((0, ast_js_1.isUndefined)(right)) {
            checkCastedType(functionDeclaration, left, context);
        }
        else if ((0, ast_js_1.isUndefined)(left)) {
            checkCastedType(functionDeclaration, right, context);
        }
    }
    else if (isBooleanCall(returnedExpression)) {
        checkCastedType(functionDeclaration, returnedExpression.arguments[0], context);
    }
    else if (isNegation(returnedExpression) && isNegation(returnedExpression.argument)) {
        checkCastedType(functionDeclaration, returnedExpression.argument.argument, context);
    }
}
function getReturnedExpression(block) {
    if (block?.body.length === 1) {
        const statement = block.body[0];
        if (statement.type === 'ReturnStatement') {
            return statement.argument;
        }
    }
    return undefined;
}
function isInequalityBinaryExpression(returnExpression) {
    return (returnExpression.type === 'BinaryExpression' &&
        (returnExpression.operator === '!==' || returnExpression.operator === '!='));
}
function checkCastedType(node, expression, context) {
    const sourceCode = context.sourceCode;
    const castedType = getCastTupleFromMemberExpression(expression);
    if (castedType && castedType[1].type !== 'TSAnyKeyword') {
        const nOfParam = node.params.length;
        if (nOfParam === 1 || (nOfParam === 0 && castedType[0].type === 'ThisExpression')) {
            const castedExpressionText = sourceCode.getText(castedType[0]);
            const castedTypeText = sourceCode.getText(castedType[1]);
            const predicate = `: ${castedExpressionText} is ${castedTypeText}`;
            const suggest = getTypePredicateSuggestion(node, context, predicate);
            context.report({
                messageId: 'useTypePredicate',
                data: {
                    castedExpressionText,
                    castedTypeText,
                },
                loc: (0, location_js_1.getMainFunctionTokenLocation)(node, (0, ancestor_js_1.getParent)(context, node), context),
                suggest,
            });
        }
    }
}
function getTypePredicateSuggestion(node, context, predicate) {
    const suggestions = [];
    let fix;
    if (node.returnType) {
        fix = fixer => fixer.replaceText(node.returnType, predicate);
    }
    else {
        const closingParenthesis = context.sourceCode.getTokenBefore(node.body, token => token.value === ')');
        fix = fixer => fixer.insertTextAfter(closingParenthesis, predicate);
    }
    suggestions.push({ messageId: 'suggestTypePredicate', fix });
    return suggestions;
}
function getCastTupleFromMemberExpression(node) {
    if (node.type === 'MemberExpression') {
        const object = node.object;
        if (object.type === 'TSAsExpression' || object.type === 'TSTypeAssertion') {
            return [object.expression, object.typeAnnotation];
        }
    }
    return undefined;
}
function isNegation(node) {
    return node.type === 'UnaryExpression' && node.prefix && node.operator === '!';
}
function isBooleanCall(node) {
    if (node.type === 'CallExpression') {
        const callee = node.callee;
        return node.arguments.length === 1 && callee.type === 'Identifier' && callee.name === 'Boolean';
    }
    return false;
}
