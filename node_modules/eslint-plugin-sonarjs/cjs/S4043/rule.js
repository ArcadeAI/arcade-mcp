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
// https://sonarsource.github.io/rspec/#/rspec/S4043/javascript
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
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.rule = void 0;
const typescript_1 = __importDefault(require("typescript"));
const parser_services_js_1 = require("../helpers/parser-services.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const type_js_1 = require("../helpers/type.js");
const ancestor_js_1 = require("../helpers/ancestor.js");
const collection_js_1 = require("../helpers/collection.js");
const meta = __importStar(require("./generated-meta.js"));
const arrayMutatingMethods = new Set(['reverse', "'reverse'", '"reverse"', ...collection_js_1.sortLike]);
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        hasSuggestions: true,
        messages: {
            moveMethod: 'Move this array "{{method}}" operation to a separate statement or replace it with "{{suggestedMethod}}".',
            suggestMethod: 'Replace with "{{suggestedMethod}}" method',
        },
    }),
    create(context) {
        const services = context.sourceCode.parserServices;
        if (!(0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {};
        }
        return {
            CallExpression(node) {
                const { callee } = node;
                if (callee.type === 'MemberExpression') {
                    const propertyText = context.sourceCode.getText(callee.property);
                    if (isArrayMutatingCall(callee, services, propertyText)) {
                        const mutatedArray = callee.object;
                        if (isIdentifierOrPropertyAccessExpression(mutatedArray, services) &&
                            !isInSelfAssignment(mutatedArray, node) &&
                            isForbiddenOperation(node)) {
                            const method = formatMethod(propertyText);
                            const suggestedMethod = method === 'sort' ? 'toSorted' : 'toReversed';
                            context.report({
                                messageId: 'moveMethod',
                                data: {
                                    method,
                                    suggestedMethod,
                                },
                                node,
                                suggest: [
                                    {
                                        messageId: 'suggestMethod',
                                        data: {
                                            suggestedMethod,
                                        },
                                        fix: fixer => {
                                            const fixedPropertyText = propertyText.replace(method, suggestedMethod);
                                            return fixer.replaceText(callee.property, fixedPropertyText);
                                        },
                                    },
                                ],
                            });
                        }
                    }
                }
            },
        };
    },
};
function formatMethod(mutatingMethod) {
    if (mutatingMethod.startsWith('"') || mutatingMethod.startsWith("'")) {
        return mutatingMethod.substring(1, mutatingMethod.length - 1);
    }
    else {
        return mutatingMethod;
    }
}
function isArrayMutatingCall(memberExpression, services, propertyText) {
    return arrayMutatingMethods.has(propertyText) && (0, type_js_1.isArray)(memberExpression.object, services);
}
function isIdentifierOrPropertyAccessExpression(node, services) {
    return (node.type === 'Identifier' ||
        (node.type === 'MemberExpression' && !isGetAccessor(node.property, services)));
}
function isGetAccessor(node, services) {
    const symbol = (0, type_js_1.getSymbolAtLocation)(node, services);
    const declarations = symbol?.declarations;
    return declarations?.length === 1 && declarations[0].kind === typescript_1.default.SyntaxKind.GetAccessor;
}
function isInSelfAssignment(mutatedArray, node) {
    const parent = node.parent;
    return (
    // check assignment
    parent?.type === 'AssignmentExpression' &&
        parent.operator === '=' &&
        parent.left.type === 'Identifier' &&
        mutatedArray.type === 'Identifier' &&
        parent.left.name === mutatedArray.name);
}
function isForbiddenOperation(node) {
    return !isStandaloneExpression(node) && !isReturnedExpression(node);
}
function isStandaloneExpression(node) {
    const ancestors = (0, ancestor_js_1.localAncestorsChain)(node);
    const returnIdx = ancestors.findIndex(ancestor => ancestor.type === 'ExpressionStatement');
    return (returnIdx > -1 &&
        ancestors
            .slice(0, returnIdx)
            .every(ancestor => ['ChainExpression', 'LogicalExpression'].includes(ancestor.type)));
}
function isReturnedExpression(node) {
    const ancestors = (0, ancestor_js_1.localAncestorsChain)(node);
    const returnIdx = ancestors.findIndex(ancestor => ancestor.type === 'ReturnStatement');
    return (returnIdx > -1 &&
        ancestors
            .slice(0, returnIdx)
            .every(ancestor => ['ArrayExpression', 'ObjectExpression', 'ConditionalExpression', 'SpreadElement'].includes(ancestor.type)));
}
