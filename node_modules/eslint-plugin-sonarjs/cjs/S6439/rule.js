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
// https://sonarsource.github.io/rspec/#/rspec/S6439/javascript
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
const type_js_1 = require("../helpers/type.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const meta = __importStar(require("./generated-meta.js"));
const detectReactNativeSelector = [
    ':matches(',
    [
        'CallExpression[callee.name="require"][arguments.0.value="react-native"]',
        'ImportDeclaration[source.value="react-native"]',
    ].join(','),
    ')',
].join('');
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        hasSuggestions: true,
        messages: {
            nonBooleanMightRender: 'Convert the conditional to a boolean to avoid leaked value',
            suggestConversion: 'Convert the conditional to a boolean',
        },
    }),
    create(context) {
        if (!(0, parser_services_js_1.isRequiredParserServices)(context.sourceCode.parserServices)) {
            return {};
        }
        let usesReactNative = false;
        return {
            [detectReactNativeSelector]() {
                usesReactNative = true;
            },
            'JSXExpressionContainer > LogicalExpression[operator="&&"]'(node) {
                const leftSide = node.left;
                checkNonBoolean(context, usesReactNative ? isStringOrNumber : isNumber, leftSide);
            },
        };
    },
};
function report(node, context) {
    context.report({
        messageId: 'nonBooleanMightRender',
        node,
        suggest: [
            {
                messageId: 'suggestConversion',
                fix: fixer => {
                    const sourceCode = context.sourceCode;
                    const previousToken = sourceCode.getTokenBefore(node);
                    const nextToken = sourceCode.getTokenAfter(node);
                    const fixes = [];
                    if (!!previousToken &&
                        !!nextToken &&
                        node.range !== undefined &&
                        previousToken.value === '(' &&
                        previousToken.range[1] <= node.range[0] &&
                        nextToken.value === ')' &&
                        nextToken.range[0] >= node.range[1]) {
                        fixes.push(fixer.remove(previousToken), fixer.remove(nextToken));
                    }
                    fixes.push(fixer.replaceText(node, `!!(${sourceCode.getText(node)})`));
                    return fixes;
                },
            },
        ],
    });
}
function isStringOrNumber(node, context) {
    const type = (0, type_js_1.getTypeFromTreeNode)(node, context.sourceCode.parserServices);
    return (0, type_js_1.isStringType)(type) || (0, type_js_1.isBigIntType)(type) || (0, type_js_1.isNumberType)(type);
}
function isNumber(node, context) {
    const type = (0, type_js_1.getTypeFromTreeNode)(node, context.sourceCode.parserServices);
    return (0, type_js_1.isBigIntType)(type) || (0, type_js_1.isNumberType)(type);
}
function checkNonBoolean(context, isLeakingType, node) {
    if (node.type === 'LogicalExpression') {
        checkNonBoolean(context, isLeakingType, node.left);
        checkNonBoolean(context, isLeakingType, node.right);
    }
    else if (isLeakingType(node, context)) {
        report(node, context);
    }
}
