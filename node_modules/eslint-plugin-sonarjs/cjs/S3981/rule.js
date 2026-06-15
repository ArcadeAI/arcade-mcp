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
// https://sonarsource.github.io/rspec/#/rspec/S3981
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
const parser_services_js_1 = require("../helpers/parser-services.js");
const meta = __importStar(require("./generated-meta.js"));
const CollectionLike = new Set(['Array', 'Map', 'Set', 'WeakMap', 'WeakSet']);
const CollectionSizeLike = new Set(['length', 'size']);
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            fixCollectionSizeCheck: 'Fix this expression; {{propertyName}} of "{{objectName}}" is always greater or equal to zero.',
            suggestFixedSizeCheck: 'Use "{{operator}}" for {{operation}} check',
        },
        hasSuggestions: true,
    }),
    create(context) {
        const services = context.sourceCode.parserServices;
        const isTypeCheckerAvailable = (0, parser_services_js_1.isRequiredParserServices)(services);
        return {
            BinaryExpression: (node) => {
                if (['<', '>='].includes(node.operator)) {
                    const lhs = node.left;
                    const rhs = node.right;
                    if (isZeroLiteral(rhs) && lhs.type === 'MemberExpression') {
                        const { object, property } = lhs;
                        if (property.type === 'Identifier' &&
                            CollectionSizeLike.has(property.name) &&
                            (!isTypeCheckerAvailable || isCollection(object, services))) {
                            context.report({
                                messageId: 'fixCollectionSizeCheck',
                                data: {
                                    propertyName: property.name,
                                    objectName: context.sourceCode.getText(object),
                                },
                                node,
                                suggest: getSuggestion(node, property.name, context),
                            });
                        }
                    }
                }
            },
        };
    },
};
function isZeroLiteral(node) {
    return node.type === 'Literal' && node.value === 0;
}
function isCollection(node, services) {
    const checker = services.program.getTypeChecker();
    const tp = checker.getTypeAtLocation(services.esTreeNodeToTSNodeMap.get(node));
    return !!tp.symbol && CollectionLike.has(tp.symbol.name);
}
function getSuggestion(expr, operation, context) {
    const { left, operator } = expr;
    const operatorToken = context.sourceCode.getTokenAfter(left, token => token.value === operator);
    const fixedOperator = operator === '<' ? '==' : '>';
    return [
        {
            messageId: 'suggestFixedSizeCheck',
            data: {
                operation,
                operator: fixedOperator,
            },
            fix: fixer => fixer.replaceText(operatorToken, fixedOperator),
        },
    ];
}
