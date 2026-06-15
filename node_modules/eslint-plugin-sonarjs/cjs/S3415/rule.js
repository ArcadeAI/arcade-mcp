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
// https://sonarsource.github.io/rspec/#/rspec/S3415/javascript
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
const mocha_js_1 = require("../helpers/mocha.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
const ASSERT_FUNCTIONS = [
    'equal',
    'notEqual',
    'strictEqual',
    'notStrictEqual',
    'deepEqual',
    'notDeepEqual',
    'closeTo',
    'approximately',
];
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, { hasSuggestions: true }),
    create(context) {
        const testCases = [];
        return {
            CallExpression(node) {
                if ((0, mocha_js_1.isTestCase)(node)) {
                    testCases.push(node);
                    return;
                }
                if (testCases.length > 0) {
                    checkInvertedArguments(node, context);
                }
            },
            'CallExpression:exit': (node) => {
                if ((0, mocha_js_1.isTestCase)(node)) {
                    testCases.pop();
                }
            },
        };
    },
};
function checkInvertedArguments(node, context) {
    const args = extractAssertionsArguments(node);
    if (args) {
        const [actual, expected, format] = args;
        if ((0, ast_js_1.isLiteral)(actual) && !(0, ast_js_1.isLiteral)(expected)) {
            (0, location_js_1.report)(context, {
                node: expected,
                message: `Swap these 2 arguments so they are in the correct order: ${format}.`,
                suggest: [
                    {
                        desc: 'Swap arguments',
                        fix: fixer => [
                            fixer.replaceText(actual, context.sourceCode.getText(expected)),
                            fixer.replaceText(expected, context.sourceCode.getText(actual)),
                        ],
                    },
                ],
            }, [(0, location_js_1.toSecondaryLocation)(actual, 'Other argument to swap.')]);
        }
    }
}
function extractAssertionsArguments(node) {
    return extractAssertArguments(node) ?? extractExpectArguments(node) ?? extractFailArguments(node);
}
function extractAssertArguments(node) {
    if ((0, ast_js_1.isMethodCall)(node) && node.arguments.length > 1) {
        const { callee: { object, property }, arguments: [actual, expected], } = node;
        if ((0, ast_js_1.isIdentifier)(object, 'assert') && (0, ast_js_1.isIdentifier)(property, ...ASSERT_FUNCTIONS)) {
            return [actual, expected, `${object.name}.${property.name}(actual, expected)`];
        }
    }
    return null;
}
function extractExpectArguments(node) {
    if (node.callee.type !== 'MemberExpression') {
        return null;
    }
    let { object, property } = node.callee;
    if (!(0, ast_js_1.isIdentifier)(property, 'equal', 'eql', 'closeTo')) {
        return null;
    }
    while (object.type === 'MemberExpression') {
        object = object.object;
    }
    if (object.type === 'CallExpression' && (0, ast_js_1.isIdentifier)(object.callee, 'expect')) {
        return [
            object.arguments[0],
            node.arguments[0],
            `${object.callee.name}(actual).to.${property.name}(expected)`,
        ];
    }
    return null;
}
function extractFailArguments(node) {
    if ((0, ast_js_1.isMethodCall)(node) && node.arguments.length > 1) {
        const { callee: { object, property }, arguments: [actual, expected], } = node;
        if ((0, ast_js_1.isIdentifier)(object, 'assert', 'expect', 'should') && (0, ast_js_1.isIdentifier)(property, 'fail')) {
            return [actual, expected, `${object.name}.${property.name}(actual, expected)`];
        }
    }
    return null;
}
