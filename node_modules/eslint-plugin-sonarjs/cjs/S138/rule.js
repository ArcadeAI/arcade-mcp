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
// Greatly inspired by https://github.com/eslint/eslint/blob/561b6d4726f3e77dd40ba0d340ca7f08429cd2eb/lib/rules/max-lines-per-function.js
// We had to fork the implementation to control the reporting (issue location), in order to provide a better user experience.
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
exports.getLocsNumber = getLocsNumber;
exports.getCommentLineNumbers = getCommentLineNumbers;
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const location_js_1 = require("../helpers/location.js");
const ancestor_js_1 = require("../helpers/ancestor.js");
const collection_js_1 = require("../helpers/collection.js");
const meta = __importStar(require("./generated-meta.js"));
const DEFAULT = 200;
const messages = {
    functionMaxLine: 'This function has {{lineCount}} lines, which is greater than the {{threshold}} lines authorized. Split it into smaller functions.',
};
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, { messages }),
    create(context) {
        const threshold = context.options[0]?.maximum ?? DEFAULT;
        const sourceCode = context.sourceCode;
        const lines = sourceCode.lines;
        const commentLineNumbers = getCommentLineNumbers(sourceCode.getAllComments());
        const functionStack = [];
        const functionKnowledge = new Map();
        return {
            'FunctionDeclaration, FunctionExpression, ArrowFunctionExpression': (node) => {
                functionStack.push(node);
                const parent = (0, ancestor_js_1.getParent)(context, node);
                if (!node.loc || isIIFE(node, parent)) {
                    return;
                }
                const lineCount = getLocsNumber(node.loc, lines, commentLineNumbers);
                const startsWithCapital = nameStartsWithCapital(node);
                functionKnowledge.set(node, { node, lineCount, startsWithCapital, returnsJSX: false });
            },
            ReturnStatement: (node) => {
                const returnStatement = node;
                const knowledge = functionKnowledge.get((0, collection_js_1.last)(functionStack));
                if (knowledge &&
                    returnStatement.argument &&
                    returnStatement.argument.type.startsWith('JSX')) {
                    knowledge.returnsJSX = true;
                }
            },
            'FunctionDeclaration:exit': () => {
                functionStack.pop();
            },
            'FunctionExpression:exit': () => {
                functionStack.pop();
            },
            'ArrowFunctionExpression:exit': () => {
                functionStack.pop();
            },
            'Program:exit': () => {
                for (const knowledge of functionKnowledge.values()) {
                    const { node, lineCount } = knowledge;
                    if (lineCount > threshold && !isReactFunctionComponent(knowledge)) {
                        const functionLike = node;
                        context.report({
                            messageId: 'functionMaxLine',
                            data: {
                                lineCount: lineCount.toString(),
                                threshold: `${threshold}`,
                            },
                            loc: (0, location_js_1.getMainFunctionTokenLocation)(functionLike, functionLike.parent, context),
                        });
                    }
                }
            },
        };
    },
};
function getLocsNumber(loc, lines, commentLineNumbers) {
    let lineCount = 0;
    for (let i = loc.start.line - 1; i < loc.end.line; ++i) {
        const line = lines[i];
        const comment = commentLineNumbers.get(i + 1);
        if (comment && isFullLineComment(line, i + 1, comment)) {
            continue;
        }
        if (/^\s*$/u.test(line)) {
            continue;
        }
        lineCount++;
    }
    return lineCount;
}
function getCommentLineNumbers(comments) {
    const map = new Map();
    for (const comment of comments) {
        if (comment.loc) {
            for (let i = comment.loc.start.line; i <= comment.loc.end.line; i++) {
                map.set(i, comment);
            }
        }
    }
    return map;
}
function isFullLineComment(line, lineNumber, comment) {
    if (!comment.loc) {
        return false;
    }
    const { start, end } = comment.loc;
    const isFirstTokenOnLine = start.line === lineNumber && !line.slice(0, start.column).trim();
    const isLastTokenOnLine = end.line === lineNumber && !line.slice(end.column).trim();
    return (comment &&
        (start.line < lineNumber || isFirstTokenOnLine) &&
        (end.line > lineNumber || isLastTokenOnLine));
}
function isIIFE(node, parent) {
    return (node.type === 'FunctionExpression' &&
        parent?.type === 'CallExpression' &&
        parent.callee === node);
}
function isReactFunctionComponent(knowledge) {
    return knowledge.startsWithCapital && knowledge.returnsJSX;
}
function nameStartsWithCapital(node) {
    const identifier = getIdentifierFromNormalFunction(node) ?? getIdentifierFromArrowFunction(node);
    if (!identifier) {
        return false;
    }
    return isIdentifierUppercase(identifier);
    /**
     * Picks `Foo` from: `let Foo = () => {}`
     */
    function getIdentifierFromArrowFunction(node) {
        if (node.type !== 'ArrowFunctionExpression') {
            return null;
        }
        const parent = (0, ancestor_js_1.getNodeParent)(node);
        if (!parent) {
            return null;
        }
        if (parent.type === 'VariableDeclarator') {
            return parent.id;
        }
        else {
            return null;
        }
    }
    /**
     * Picks `Foo` from:
     * - `function Foo() {}`
     * - `let bar = function Foo() {}`
     */
    function getIdentifierFromNormalFunction(node) {
        if (node.type === 'FunctionDeclaration' || node.type === 'FunctionExpression') {
            return node.id;
        }
    }
    function isIdentifierUppercase(node) {
        return node.name.startsWith(node.name[0].toUpperCase());
    }
}
