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
// https://sonarsource.github.io/rspec/#/rspec/S1529/javascript
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
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const type_js_1 = require("../helpers/type.js");
const meta = __importStar(require("./generated-meta.js"));
const BITWISE_AND_OR = new Set(['&', '|']);
const BITWISE_OPERATORS = new Set([
    '&',
    '|',
    '^',
    '~',
    '<<',
    '>>',
    '>>>',
    '&=',
    '|=',
    '^=',
    '<<=',
    '>>=',
    '>>>=',
]);
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const isNumeric = getNumericTypeChecker(context);
        let lonelyBitwiseAndOr = null;
        let lonelyBitwiseAndOrAncestors = [];
        let fileContainsSeveralBitwiseOperations = false;
        return {
            BinaryExpression(node) {
                const expression = node;
                if (!lonelyBitwiseAndOr &&
                    BITWISE_AND_OR.has(expression.operator) &&
                    !isNumeric(expression.left) &&
                    !isNumeric(expression.right)) {
                    lonelyBitwiseAndOr = expression;
                    lonelyBitwiseAndOrAncestors = [...context.sourceCode.getAncestors(node)];
                }
                else if (BITWISE_OPERATORS.has(expression.operator)) {
                    fileContainsSeveralBitwiseOperations = true;
                }
            },
            'Program:exit'() {
                if (!fileContainsSeveralBitwiseOperations &&
                    lonelyBitwiseAndOr &&
                    insideCondition(lonelyBitwiseAndOr, lonelyBitwiseAndOrAncestors)) {
                    const op = lonelyBitwiseAndOr.operator;
                    const operatorToken = context.sourceCode.getTokenAfter(lonelyBitwiseAndOr.left);
                    if (operatorToken) {
                        context.report({
                            loc: operatorToken.loc,
                            message: `Review this use of bitwise "${op}" operator; conditional "${op}${op}" might have been intended.`,
                        });
                    }
                }
            },
        };
    },
};
function insideCondition(node, ancestors) {
    let child = node;
    for (let i = ancestors.length - 1; i >= 0; i--) {
        const parent = ancestors[i];
        if (parent.type === 'IfStatement' ||
            parent.type === 'ForStatement' ||
            parent.type === 'WhileStatement' ||
            parent.type === 'DoWhileStatement' ||
            parent.type === 'ConditionalExpression') {
            return parent.test === child;
        }
        child = parent;
    }
    return false;
}
function getNumericTypeChecker(context) {
    const services = context.sourceCode.parserServices;
    if (!!services && !!services.program && !!services.esTreeNodeToTSNodeMap) {
        return (node) => isNumericType((0, type_js_1.getTypeFromTreeNode)(node, services));
    }
    else {
        const numericTypes = new Set(['number', 'bigint']);
        return (node) => node.type === 'Literal' ? numericTypes.has(typeof node.value) : false;
    }
}
function isNumericType(type) {
    return ((type.getFlags() & (typescript_1.default.TypeFlags.NumberLike | typescript_1.default.TypeFlags.BigIntLike)) !== 0 ||
        (type.isUnionOrIntersection() && type.types.some(isNumericType)));
}
