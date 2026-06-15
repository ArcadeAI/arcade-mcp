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
// https://sonarsource.github.io/rspec/#/rspec/S125/javascript
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
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const collection_js_1 = require("../helpers/collection.js");
const meta = __importStar(require("./generated-meta.js"));
const CodeRecognizer_js_1 = require("../helpers/recognizers/CodeRecognizer.js");
const JavaScriptFootPrint_js_1 = require("../helpers/recognizers/JavaScriptFootPrint.js");
const node_path_1 = __importDefault(require("node:path"));
const EXCLUDED_STATEMENTS = new Set(['BreakStatement', 'LabeledStatement', 'ContinueStatement']);
// Documentation example prefixes that indicate a comment is an intentional usage example,
// not commented-out dead code (e.g. "e.g. foo()", "example: bar()").
const DOCUMENTATION_PREFIX_PATTERN = /^(e\.g[.:]|for example\b|examples?:)/i;
// Cheap prefilter: any meaningful JS statement must contain at least one of these characters,
// or be an import/export with a string literal (side-effect imports have no punctuation)
const CODE_CHAR_PATTERN = /[;{}()=<>]|\bimport\s+['"]|\bexport\s/;
const JSX_ATTRIBUTE_WRAPPER = '_S125Wrapper';
const recognizer = new CodeRecognizer_js_1.CodeRecognizer(0.9, new JavaScriptFootPrint_js_1.JavaScriptFootPrint());
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            commentedCode: 'Remove this commented out code.',
            commentedCodeFix: 'Remove this commented out code',
        },
        hasSuggestions: true,
    }),
    create(context) {
        function getGroupedComments(comments) {
            const groupedComments = [];
            let currentGroup = [];
            for (const comment of comments) {
                if (comment.type === 'Block') {
                    groupedComments.push({ value: comment.value, nodes: [comment] });
                }
                else if (currentGroup.length === 0 ||
                    areAdjacentLineComments((0, collection_js_1.last)(currentGroup), comment)) {
                    currentGroup.push(comment);
                }
                else {
                    groupedComments.push({
                        value: currentGroup.map(lineComment => lineComment.value).join('\n'),
                        nodes: currentGroup,
                    });
                    currentGroup = [comment];
                }
            }
            if (currentGroup.length > 0) {
                groupedComments.push({
                    value: currentGroup.map(lineComment => lineComment.value).join('\n'),
                    nodes: currentGroup,
                });
            }
            return groupedComments;
        }
        function areAdjacentLineComments(previous, next) {
            const nextCommentLine = next.loc.start.line;
            if (previous.loc.start.line + 1 === nextCommentLine) {
                const nextCodeToken = context.sourceCode.getTokenAfter(previous);
                return !nextCodeToken || nextCodeToken.loc.start.line > nextCommentLine;
            }
            return false;
        }
        return {
            'Program:exit': () => {
                const groupedComments = getGroupedComments(context.sourceCode.getAllComments());
                for (const groupComment of groupedComments) {
                    const rawTextTrimmed = groupComment.value.trim();
                    if (rawTextTrimmed !== '}' &&
                        !isDocumentationExample(rawTextTrimmed) &&
                        containsCode(injectMissingBraces(rawTextTrimmed), context)) {
                        context.report({
                            messageId: 'commentedCode',
                            loc: getCommentLocation(groupComment.nodes),
                            suggest: [
                                {
                                    messageId: 'commentedCodeFix',
                                    fix(fixer) {
                                        const start = groupComment.nodes[0].range[0];
                                        const end = (0, collection_js_1.last)(groupComment.nodes).range[1];
                                        return fixer.removeRange([start, end]);
                                    },
                                },
                            ],
                        });
                    }
                }
            },
        };
    },
};
function isExpressionExclusion(statement, value, program, context) {
    if (statement.type === 'ExpressionStatement') {
        const expression = statement.expression;
        if (expression.type === 'Identifier' ||
            expression.type === 'SequenceExpression' ||
            isUnaryPlusOrMinus(expression) ||
            isExcludedLiteral(expression)) {
            return true;
        }
        // Only construct SourceCode when we need getLastToken.
        // Access the constructor from context to avoid a static runtime import of 'eslint'.
        const SourceCodeClass = context.sourceCode.constructor;
        const code = new SourceCodeClass(value, program);
        return !code.getLastToken(statement, token => token.value === ';');
    }
    return false;
}
function isExclusion(parsedBody, value, program, context) {
    if (parsedBody.length === 1) {
        const singleStatement = parsedBody[0];
        return (EXCLUDED_STATEMENTS.has(singleStatement.type) ||
            isReturnThrowExclusion(singleStatement) ||
            isExpressionExclusion(singleStatement, value, program, context));
    }
    return false;
}
function containsCode(value, context) {
    if (!CODE_CHAR_PATTERN.test(value) || !couldBeJsCode(value) || !context.languageOptions.parser) {
        return false;
    }
    const options = {
        ...context.languageOptions?.parserOptions,
        filePath: `placeholder${node_path_1.default.extname(context.filename)}`,
        programs: undefined,
        project: undefined,
    };
    //In case of Vue parser: we will use the JS/TS parser instead of the Vue parser
    const parser = context.languageOptions?.parserOptions?.parser ?? context.languageOptions?.parser;
    const program = parseWithRuleParser(value, parser, options);
    if (program) {
        return program.body.length > 0 && !isExclusion(program.body, value, program, context);
    }
    const wrappedProgram = parseWithRuleParser(wrapAsJsxTag(value), parser, options);
    return hasValidJsxAttributeCode(wrappedProgram);
}
function couldBeJsCode(input) {
    return input.split('\n').some(line => recognizer.recognition(line) >= recognizer.threshold);
}
function injectMissingBraces(value) {
    let balance = 0;
    let minBalance = 0;
    for (const char of value) {
        if (char === '{') {
            balance++;
        }
        else if (char === '}') {
            balance--;
            if (balance < minBalance) {
                minBalance = balance;
            }
        }
    }
    const openToAdd = -minBalance;
    const closeToAdd = balance - minBalance;
    if (openToAdd > 0 || closeToAdd > 0) {
        return '{'.repeat(openToAdd) + value + '}'.repeat(closeToAdd);
    }
    return value;
}
function getCommentLocation(nodes) {
    return {
        start: nodes[0].loc.start,
        end: (0, collection_js_1.last)(nodes).loc.end,
    };
}
function isReturnThrowExclusion(statement) {
    if (statement.type === 'ReturnStatement' || statement.type === 'ThrowStatement') {
        return statement.argument == null || statement.argument.type === 'Identifier';
    }
    return false;
}
function isUnaryPlusOrMinus(expression) {
    return (expression.type === 'UnaryExpression' &&
        (expression.operator === '+' || expression.operator === '-'));
}
function isExcludedLiteral(expression) {
    if (expression.type === 'Literal') {
        return typeof expression.value === 'string' || typeof expression.value === 'number';
    }
    return false;
}
function isDocumentationExample(value) {
    const firstLine = value.split('\n')[0];
    // Strip any leading '//' markers (e.g. '// foo()' in a nested comment becomes 'foo()')
    const stripped = firstLine.replace(/^(?:\/\/\s*)+/, '').trim();
    return DOCUMENTATION_PREFIX_PATTERN.test(stripped);
}
function parseWithRuleParser(value, parser, options) {
    try {
        return ('parse' in parser ? parser.parse(value, options) : parser.parseForESLint(value, options).ast);
    }
    catch {
        return null;
    }
}
function wrapAsJsxTag(value) {
    return `<${JSX_ATTRIBUTE_WRAPPER} ${value} />`;
}
function hasValidJsxAttributeCode(program) {
    if (program?.body.length !== 1) {
        return false;
    }
    const statement = program.body[0];
    if (statement.type !== 'ExpressionStatement' || statement.expression.type !== 'JSXElement') {
        return false;
    }
    const jsxElement = statement.expression;
    if (jsxElement.openingElement.name.type !== 'JSXIdentifier') {
        return false;
    }
    if (jsxElement.openingElement.name.name !== JSX_ATTRIBUTE_WRAPPER) {
        return false;
    }
    const attributes = jsxElement.openingElement.attributes;
    return attributes.length > 0 && attributes.every(isValidJsxAttribute);
}
function isValidJsxAttribute(attribute) {
    if (attribute.type === 'JSXSpreadAttribute') {
        return true;
    }
    if (attribute.name.type !== 'JSXIdentifier') {
        return false;
    }
    return attribute.value !== null;
}
