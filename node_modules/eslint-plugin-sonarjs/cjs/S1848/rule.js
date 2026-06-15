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
// https://sonarsource.github.io/rspec/#/rspec/S1848/javascript
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
const module_js_1 = require("../helpers/module.js");
const reaching_definitions_js_1 = require("../helpers/reaching-definitions.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
/** DOM selection method names commonly used for element selection */
const DOM_SELECTION_METHODS = [
    'querySelector',
    'querySelectorAll',
    'getElementById',
    'getElementsByClassName',
    'getElementsByTagName',
    'getElementsByName',
];
/** jQuery/$ function names */
const JQUERY_IDENTIFIERS = ['$', 'jQuery'];
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            removeInstantiationOf: 'Either remove this useless object instantiation of "{{constructor}}" or use it.',
            removeInstantiation: 'Either remove this useless object instantiation or use it.',
        },
    }),
    create(context) {
        const sourceCode = context.sourceCode;
        return {
            'ExpressionStatement > NewExpression': (node) => {
                if (isTryable(node, context)) {
                    return;
                }
                // Skip constructors receiving DOM elements - indicates DOM attachment side effect
                if (hasDomSelectionArgument(node, context)) {
                    return;
                }
                const { callee } = node;
                if (callee.type === 'Identifier' || callee.type === 'MemberExpression') {
                    const calleeText = sourceCode.getText(callee);
                    if (isException(context, callee, calleeText)) {
                        return;
                    }
                    const reportLocation = {
                        start: node.loc.start,
                        end: callee.loc.end,
                    };
                    reportIssue(reportLocation, `${calleeText}`, 'removeInstantiationOf', context);
                }
                else {
                    const newToken = sourceCode.getFirstToken(node);
                    reportIssue(newToken.loc, '', 'removeInstantiation', context);
                }
            },
        };
    },
};
function isTryable(node, context) {
    const ancestors = context.sourceCode.getAncestors(node);
    let parent = undefined;
    let child = node;
    while ((parent = ancestors.pop()) !== undefined) {
        if (parent.type === 'TryStatement' && parent.block === child) {
            return true;
        }
        child = parent;
    }
    return false;
}
function reportIssue(loc, objectText, messageId, context) {
    context.report({
        messageId,
        data: {
            constructor: objectText,
        },
        loc,
    });
}
/**
 * These exceptions are based on community requests and Peach
 */
function isException(context, node, name) {
    if (name === 'Notification') {
        return true;
    }
    const fqn = (0, module_js_1.getFullyQualifiedName)(context, node);
    if (!fqn) {
        return false;
    }
    const exactExceptions = ['vue', '@ag-grid-community.core.Grid'];
    const startsWithExceptions = ['aws-cdk-lib', 'cdk8s', '@pulumi', '@cdktf', 'obsidian'];
    return (exactExceptions.includes(fqn) ||
        startsWithExceptions.some(exception => fqn.startsWith(exception)));
}
/**
 * Checks if any constructor argument contains a DOM selection call.
 * Constructors receiving DOM elements typically attach to them on construction.
 */
function hasDomSelectionArgument(node, context) {
    const scope = context.sourceCode.getScope(node);
    return node.arguments.some(arg => arg.type !== 'SpreadElement' && containsDomSelection(arg, scope));
}
/**
 * Recursively checks if a node contains a DOM selection call.
 * Also resolves variables to check if they were initialized from DOM selection.
 */
function containsDomSelection(node, scope) {
    if (node.type === 'CallExpression') {
        return isDomSelectionCall(node);
    }
    if (node.type === 'Identifier') {
        // Resolve variable to check its initializer
        return isVariableFromDomSelection(node, scope);
    }
    if (node.type === 'MemberExpression') {
        // Check if object is a DOM selection call (e.g., document.querySelector(...).dataset)
        return containsDomSelection(node.object, scope);
    }
    if (node.type === 'ObjectExpression') {
        // Check properties for DOM selection calls (e.g., {element: $('foo')})
        return node.properties.some(prop => {
            if (prop.type === 'Property') {
                return containsDomSelection(prop.value, scope);
            }
            return false;
        });
    }
    if (node.type === 'ArrayExpression') {
        // Check array elements for DOM selection calls (e.g., [$('foo'), $('bar')])
        return node.elements.some(elem => elem !== null && containsDomSelection(elem, scope));
    }
    if (node.type === 'ConditionalExpression') {
        return (containsDomSelection(node.consequent, scope) || containsDomSelection(node.alternate, scope));
    }
    return false;
}
/**
 * Checks if a variable was initialized from a DOM selection call.
 */
function isVariableFromDomSelection(node, scope) {
    const variable = (0, reaching_definitions_js_1.getVariableFromIdentifier)(node, scope);
    if (!variable) {
        return false;
    }
    // Check each definition of the variable
    for (const def of variable.defs) {
        if (def.type === 'Variable' && def.node.init) {
            // Check if the initializer is a DOM selection call (possibly wrapped in type assertion)
            const initExpr = unwrapTypeAssertion(def.node.init);
            if (initExpr.type === 'CallExpression' && isDomSelectionCall(initExpr)) {
                return true;
            }
        }
    }
    return false;
}
/**
 * Unwraps TypeScript type assertions to get the underlying expression.
 * Handles: x as Type, <Type>x
 */
function unwrapTypeAssertion(node) {
    // TypeScript AST types TSAsExpression and TSTypeAssertion are not in estree
    const nodeType = node.type;
    if (nodeType === 'TSAsExpression' || nodeType === 'TSTypeAssertion') {
        const expr = node.expression;
        return expr ? unwrapTypeAssertion(expr) : node;
    }
    return node;
}
/**
 * Checks if a call expression is a DOM selection call.
 * Matches: document.querySelector, document.getElementById, $(), jQuery(), this.$(),
 * and any call to DOM selection methods on any object (e.g., myDocument.querySelector)
 */
function isDomSelectionCall(node) {
    const { callee } = node;
    // Check for $() or jQuery()
    if ((0, ast_js_1.isIdentifier)(callee, ...JQUERY_IDENTIFIERS)) {
        return true;
    }
    // Check for *.querySelector, *.getElementById, etc. on any object
    // This covers document.querySelector, myDocument.querySelector, this.document.querySelector, etc.
    if (callee.type === 'MemberExpression' &&
        (0, ast_js_1.isIdentifier)(callee.property, ...DOM_SELECTION_METHODS)) {
        return true;
    }
    // Check for this.$() - common in Backbone/Marionette views
    if (callee.type === 'MemberExpression' &&
        callee.object.type === 'ThisExpression' &&
        (0, ast_js_1.isIdentifier)(callee.property, ...JQUERY_IDENTIFIERS)) {
        return true;
    }
    return false;
}
