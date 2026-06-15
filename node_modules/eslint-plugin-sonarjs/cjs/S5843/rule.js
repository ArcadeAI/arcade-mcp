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
// https://sonarsource.github.io/rspec/#/rspec/S5843/javascript
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
const regexpp_1 = require("@eslint-community/regexpp");
const location_js_1 = require("../helpers/location.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const ast_js_1 = require("../helpers/ast.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const ast_js_2 = require("../helpers/regex/ast.js");
const meta = __importStar(require("./generated-meta.js"));
const extract_js_1 = require("../helpers/regex/extract.js");
const range_js_1 = require("../helpers/regex/range.js");
const location_js_2 = require("../helpers/regex/location.js");
const DEFAULT_THRESHOLD = 20;
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const threshold = context.options[0]?.threshold ?? DEFAULT_THRESHOLD;
        const services = context.sourceCode.parserServices;
        const regexNodes = [];
        return {
            'Literal[regex]:exit': (node) => {
                regexNodes.push(node);
            },
            'NewExpression:exit': (node) => {
                if ((0, ast_js_2.isRegExpConstructor)(node)) {
                    regexNodes.push(node);
                }
            },
            'CallExpression:exit': (node) => {
                const callExpr = node;
                if ((0, parser_services_js_1.isRequiredParserServices)(services) && (0, ast_js_2.isStringRegexMethodCall)(callExpr, services)) {
                    regexNodes.push(callExpr.arguments[0]);
                }
                else if ((0, ast_js_2.isRegExpConstructor)(callExpr)) {
                    regexNodes.push(callExpr);
                }
            },
            'Program:exit': () => {
                for (const regexNode of regexNodes) {
                    checkRegexComplexity(regexNode, threshold, context);
                }
            },
        };
    },
};
function checkRegexComplexity(regexNode, threshold, context) {
    for (const regexParts of findRegexParts(regexNode, context)) {
        let complexity = 0;
        const secondaryLocations = [];
        for (const regexPart of regexParts) {
            const calculator = new ComplexityCalculator(regexPart, context);
            calculator.visit();
            for (const component of calculator.components) {
                secondaryLocations.push((0, location_js_1.toSecondaryLocation)(component.location, component.message));
            }
            complexity += calculator.complexity;
        }
        if (complexity > threshold) {
            (0, location_js_1.report)(context, {
                message: `Simplify this regular expression to reduce its complexity from ${complexity} to the ${threshold} allowed.`,
                node: regexParts[0],
            }, secondaryLocations, complexity - threshold);
        }
    }
}
function findRegexParts(node, context) {
    const finder = new RegexPartFinder(context);
    finder.find(node);
    return finder.parts;
}
class RegexPartFinder {
    constructor(context) {
        this.context = context;
        this.parts = [];
        this.handledIdentifiers = [];
    }
    find(node) {
        if ((0, ast_js_2.isRegExpConstructor)(node)) {
            this.find(node.arguments[0]);
        }
        else if ((0, ast_js_1.isRegexLiteral)(node)) {
            this.parts.push([node]);
        }
        else if ((0, ast_js_1.isStringLiteral)(node)) {
            this.parts.push([node]);
        }
        else if ((0, ast_js_1.isStaticTemplateLiteral)(node)) {
            this.parts.push([node]);
        }
        else if ((0, ast_js_1.isIdentifier)(node)) {
            if (!this.handledIdentifiers.includes(node)) {
                this.handledIdentifiers.push(node);
                const initializer = (0, ast_js_1.getUniqueWriteUsage)(this.context, node.name, node);
                if (initializer) {
                    this.find(initializer);
                }
            }
        }
        else if ((0, ast_js_1.isBinaryPlus)(node)) {
            const literals = [];
            this.findInStringConcatenation(node.left, literals);
            this.findInStringConcatenation(node.right, literals);
            if (literals.length > 0) {
                this.parts.push(literals);
            }
        }
    }
    findInStringConcatenation(node, literals) {
        if ((0, ast_js_1.isStringLiteral)(node)) {
            literals.push(node);
        }
        else if ((0, ast_js_1.isBinaryPlus)(node)) {
            this.findInStringConcatenation(node.left, literals);
            this.findInStringConcatenation(node.right, literals);
        }
        else {
            this.find(node);
        }
    }
}
class ComplexityCalculator {
    constructor(regexPart, context) {
        this.regexPart = regexPart;
        this.context = context;
        this.nesting = 1;
        this.complexity = 0;
        this.components = [];
        this.regexPartAST = (0, extract_js_1.getParsedRegex)(regexPart, context);
    }
    visit() {
        if (!this.regexPartAST) {
            return;
        }
        (0, regexpp_1.visitRegExpAST)(this.regexPartAST, {
            onAssertionEnter: (node) => {
                /* lookaround */
                if (node.kind === 'lookahead' || node.kind === 'lookbehind') {
                    const [start, end] = (0, range_js_1.getRegexpRange)(this.regexPart, node);
                    this.increaseComplexity(this.nesting, node, [
                        0,
                        -(end - start - 1) + (node.kind === 'lookahead' ? '?='.length : '?<='.length),
                    ]);
                    this.nesting++;
                    this.onDisjunctionEnter(node);
                }
            },
            onAssertionLeave: (node) => {
                /* lookaround */
                if (node.kind === 'lookahead' || node.kind === 'lookbehind') {
                    this.onDisjunctionLeave(node);
                    this.nesting--;
                }
            },
            onBackreferenceEnter: (node) => {
                this.increaseComplexity(1, node);
            },
            onCapturingGroupEnter: (node) => {
                /* disjunction */
                this.onDisjunctionEnter(node);
            },
            onCapturingGroupLeave: (node) => {
                /* disjunction */
                this.onDisjunctionLeave(node);
            },
            onCharacterClassEnter: (node) => {
                /* character class */
                const [start, end] = (0, range_js_1.getRegexpRange)(this.regexPart, node);
                this.increaseComplexity(1, node, [0, -(end - start - 1)]);
                this.nesting++;
            },
            onCharacterClassLeave: (_node) => {
                /* character class */
                this.nesting--;
            },
            onGroupEnter: (node) => {
                /* disjunction */
                this.onDisjunctionEnter(node);
            },
            onGroupLeave: (node) => {
                /* disjunction */
                this.onDisjunctionLeave(node);
            },
            onPatternEnter: (node) => {
                /* disjunction */
                this.onDisjunctionEnter(node);
            },
            onPatternLeave: (node) => {
                /* disjunction */
                this.onDisjunctionLeave(node);
            },
            onQuantifierEnter: (node) => {
                /* repetition */
                const [start] = (0, range_js_1.getRegexpRange)(this.regexPart, node);
                const [, end] = (0, range_js_1.getRegexpRange)(this.regexPart, node.element);
                this.increaseComplexity(this.nesting, node, [end - start, 0]);
                this.nesting++;
            },
            onQuantifierLeave: (_node) => {
                /* repetition */
                this.nesting--;
            },
        });
    }
    increaseComplexity(increment, node, offset) {
        this.complexity += increment;
        let message = '+' + increment;
        if (increment > 1) {
            message += ` (incl ${increment - 1} for nesting)`;
        }
        const loc = (0, location_js_2.getRegexpLocation)(this.regexPart, node, this.context, offset);
        if (loc) {
            this.components.push({
                location: {
                    loc,
                },
                message,
            });
        }
    }
    onDisjunctionEnter(node) {
        if (node.alternatives.length > 1) {
            let { alternatives } = node;
            let increment = this.nesting;
            while (alternatives.length > 1) {
                const [start, end] = (0, range_js_1.getRegexpRange)(this.regexPart, alternatives[1]);
                this.increaseComplexity(increment, alternatives[1], [-1, -(end - start)]);
                increment = 1;
                alternatives = alternatives.slice(1);
            }
            this.nesting++;
        }
    }
    onDisjunctionLeave(node) {
        if (node.alternatives.length > 1) {
            this.nesting--;
        }
    }
}
