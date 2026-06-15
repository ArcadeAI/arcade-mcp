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
// https://sonarsource.github.io/rspec/#/rspec/S2871/javascript
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
const collection_js_1 = require("../helpers/collection.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const type_js_1 = require("../helpers/type.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const meta = __importStar(require("./generated-meta.js"));
const compareNumberFunctionPlaceholder = '(a, b) => (a - b)';
const compareBigIntFunctionPlaceholder = [
    '(a, b) => {',
    '  if (a < b) {',
    '    return -1;',
    '  } else if (a > b) {',
    '    return 1;',
    '  } else {',
    '    return 0;',
    '  }',
    '}',
];
const languageSensitiveOrderPlaceholder = '(a, b) => a.localeCompare(b)';
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        hasSuggestions: true,
        messages: {
            provideCompareFunction: 'Provide a compare function to avoid sorting elements alphabetically.',
            provideCompareFunctionForArrayOfStrings: 'Provide a compare function that depends on "String.localeCompare", to reliably sort elements alphabetically.',
            suggestNumericOrder: 'Add a comparator function to sort in ascending order',
            suggestLanguageSensitiveOrder: 'Add a comparator function to sort in ascending language-sensitive order',
        },
    }),
    create(context) {
        const sourceCode = context.sourceCode;
        const services = context.sourceCode.parserServices;
        if (!(0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {};
        }
        return {
            'CallExpression[arguments.length=0][callee.type="MemberExpression"]': (call) => {
                const { object, property: node } = call.callee;
                const text = sourceCode.getText(node);
                const type = (0, type_js_1.getTypeFromTreeNode)(object, services);
                if ([...collection_js_1.sortLike, ...collection_js_1.copyingSortLike].includes(text) && (0, type_js_1.isArrayLikeType)(type, services)) {
                    const suggest = getSuggestions(call, type);
                    const messageId = getMessageId(type);
                    context.report({ node, suggest, messageId });
                }
            },
        };
        function getSuggestions(call, type) {
            const suggestions = [];
            if ((0, type_js_1.isNumberArray)(type, services)) {
                suggestions.push({
                    messageId: 'suggestNumericOrder',
                    fix: fixer(call, compareNumberFunctionPlaceholder),
                });
            }
            else if ((0, type_js_1.isBigIntArray)(type, services)) {
                suggestions.push({
                    messageId: 'suggestNumericOrder',
                    fix: fixer(call, ...compareBigIntFunctionPlaceholder),
                });
            }
            else if ((0, type_js_1.isStringArray)(type, services)) {
                suggestions.push({
                    messageId: 'suggestLanguageSensitiveOrder',
                    fix: fixer(call, languageSensitiveOrderPlaceholder),
                });
            }
            return suggestions;
        }
        function getMessageId(type) {
            if ((0, type_js_1.isStringArray)(type, services)) {
                return 'provideCompareFunctionForArrayOfStrings';
            }
            return 'provideCompareFunction';
        }
        function fixer(call, ...placeholder) {
            const closingParenthesis = sourceCode.getLastToken(call, token => token.value === ')');
            const indent = ' '.repeat(call.loc?.start.column);
            const text = placeholder.join(`\n${indent}`);
            return fixer => fixer.insertTextBefore(closingParenthesis, text);
        }
    },
};
