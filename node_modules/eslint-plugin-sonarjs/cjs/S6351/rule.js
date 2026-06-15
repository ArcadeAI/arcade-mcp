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
// https://sonarsource.github.io/rspec/#/rspec/S6351/javascript
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
const ast_js_1 = require("../helpers/ast.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const ancestor_js_1 = require("../helpers/ancestor.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
const ast_js_2 = require("../helpers/regex/ast.js");
const flags_js_1 = require("../helpers/regex/flags.js");
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const invocations = new Map();
        const regexes = [];
        const resets = new Set();
        return {
            'Literal:exit': (node) => {
                extractRegex(node, regexes);
            },
            'CallExpression:exit': (node) => {
                const callExpr = node;
                extractRegex(node, regexes);
                extractRegexInvocation(callExpr, regexes, invocations, context);
                checkWhileConditionRegex(callExpr, context);
            },
            'MemberExpression:exit': (node) => {
                extractResetRegex(node, regexes, resets, context);
            },
            'NewExpression:exit': (node) => {
                extractRegex(node, regexes);
            },
            'Program:exit': () => {
                for (const regex of regexes) {
                    checkGlobalStickyRegex(regex, context);
                }
                for (const [regex, usages] of invocations.entries()) {
                    checkMultipleInputsRegex(regex, usages, resets, context);
                }
            },
        };
    },
};
function extractRegex(node, acc) {
    if ((0, ast_js_1.isRegexLiteral)(node)) {
        const { flags } = node.regex;
        acc.push({ node, flags });
    }
    else if ((0, ast_js_2.isRegExpConstructor)(node)) {
        const flags = (0, flags_js_1.getFlags)(node) ?? '';
        acc.push({ node, flags });
    }
}
function extractRegexInvocation(callExpr, regexes, invocations, context) {
    if ((0, ast_js_1.isCallingMethod)(callExpr, 1, 'exec', 'test') &&
        callExpr.callee.object.type === 'Identifier') {
        const { object } = callExpr.callee;
        const variable = (0, ast_js_1.getVariableFromName)(context, object.name, callExpr);
        if (variable) {
            const value = (0, ast_js_1.getUniqueWriteUsage)(context, variable.name, callExpr);
            const regex = regexes.find(r => r.node === value);
            if (regex?.flags.includes('g')) {
                const usages = invocations.get(variable);
                if (usages) {
                    usages.push(callExpr);
                }
                else {
                    invocations.set(variable, [callExpr]);
                }
            }
        }
    }
}
function extractResetRegex(node, regexes, resets, context) {
    /* RegExp.prototype.lastIndex = ... */
    if ((0, ast_js_1.isDotNotation)(node) &&
        node.object.type === 'Identifier' &&
        node.property.name === 'lastIndex') {
        const parent = (0, ancestor_js_1.getParent)(context, node);
        if (parent?.type === 'AssignmentExpression' && parent.left === node) {
            const variable = (0, ast_js_1.getVariableFromName)(context, node.object.name, node);
            if (variable) {
                const value = (0, ast_js_1.getUniqueWriteUsage)(context, variable.name, node);
                const regex = regexes.find(r => r.node === value);
                if (regex) {
                    resets.add(variable);
                }
            }
        }
    }
}
function checkWhileConditionRegex(callExpr, context) {
    /* RegExp.prototype.exec() within while conditions */
    if ((0, ast_js_1.isMethodCall)(callExpr)) {
        const { object, property } = callExpr.callee;
        if (((0, ast_js_1.isRegexLiteral)(object) || (0, ast_js_2.isRegExpConstructor)(object)) && property.name === 'exec') {
            const flags = object.type === 'Literal' ? object.regex.flags : (0, flags_js_1.getFlags)(object);
            if (flags?.includes('g') && isWithinWhileCondition(callExpr, context)) {
                (0, location_js_1.report)(context, {
                    message: 'Extract this regular expression to avoid infinite loop.',
                    node: object,
                });
            }
        }
    }
}
function checkGlobalStickyRegex(regex, context) {
    /* RegExp with `g` and `y` flags */
    if (regex.flags.includes('g') && regex.flags.includes('y')) {
        (0, location_js_1.report)(context, {
            message: `Remove the 'g' flag from this regex as it is shadowed by the 'y' flag.`,
            node: regex.node,
        });
    }
}
function checkMultipleInputsRegex(regex, usages, resets, context) {
    /* RegExp.prototype.exec(input) / RegExp.prototype.test(input) */
    if (!resets.has(regex)) {
        const definition = regex.defs.find(def => def.type === 'Variable' && def.node.init);
        const uniqueInputs = new Set(usages.map(callExpr => context.sourceCode.getText(callExpr.arguments[0])));
        const regexReset = uniqueInputs.has(`''`) || uniqueInputs.has(`""`);
        if (definition && uniqueInputs.size > 1 && !regexReset) {
            const pattern = definition.node.init;
            (0, location_js_1.report)(context, {
                message: `Remove the 'g' flag from this regex as it is used on different inputs.`,
                node: pattern,
            }, usages.map((node, idx) => (0, location_js_1.toSecondaryLocation)(node, `Usage ${idx + 1}`)));
        }
    }
}
function isWithinWhileCondition(node, context) {
    const ancestors = context.sourceCode.getAncestors(node);
    let parent;
    let child = node;
    while ((parent = ancestors.pop()) !== undefined) {
        if (ast_js_1.functionLike.has(parent.type)) {
            break;
        }
        if (parent.type === 'WhileStatement' || parent.type === 'DoWhileStatement') {
            return parent.test === child;
        }
        child = parent;
    }
    return false;
}
