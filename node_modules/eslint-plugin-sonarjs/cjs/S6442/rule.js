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
// https://sonarsource.github.io/rspec/#/rspec/S6442/javascript
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
const ancestor_js_1 = require("../helpers/ancestor.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const module_js_1 = require("../helpers/module.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
const REACT_MODULE = 'react';
const REACT_PATTERN = /^[^a-z]/;
const HOOK_FUNCTION = 'useState';
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            noHookSetterInBody: 'Remove this state setter call, perhaps move it to an event handler or JSX attribute',
        },
    }),
    create(context) {
        function isHookCall(node) {
            return ((0, module_js_1.getFullyQualifiedName)(context, node) === `${REACT_MODULE}.${HOOK_FUNCTION}` &&
                node.arguments.length === 1);
        }
        function getReactComponentScope(node) {
            const scope = context.sourceCode.getScope(node);
            const isReact = (0, ast_js_1.isFunctionNode)(scope.block) && matchesReactComponentName(scope.block, 1);
            return isReact ? scope : null;
        }
        function isInsideFunctionScope(scope, node) {
            function searchUpperFunctionScope(current) {
                if (current === null) {
                    return null;
                }
                else if (current.type === 'function') {
                    return current;
                }
                else {
                    return searchUpperFunctionScope(current.upper);
                }
            }
            return (scope !== null && searchUpperFunctionScope(context.sourceCode.getScope(node)) === scope);
        }
        let reactComponentScope; // Scope.Scope of the React component render function.
        const setters = []; // Setter variables returned by the React useState() function.
        return {
            ':function'(node) {
                reactComponentScope ??= getReactComponentScope(node); // Store the top-most React component scope.
            },
            ':function:exit'(node) {
                if (context.sourceCode.getScope(node) === reactComponentScope) {
                    // Clean variables when leaving the React component scope.
                    reactComponentScope = null;
                    setters.length = 0;
                }
            },
            // Selector matching declarations like: const [count, setCount] = useState(0);
            ['VariableDeclarator[init.type="CallExpression"]' +
                ':has(ArrayPattern[elements.length=2][elements.0.type="Identifier"][elements.1.type="Identifier"])'](node) {
                if (!isInsideFunctionScope(reactComponentScope, node)) {
                    return;
                }
                const hookDeclarator = node;
                if (isHookCall(hookDeclarator.init)) {
                    const variable = (0, ast_js_1.getVariableFromName)(context, hookDeclarator.id.elements[1].name, node);
                    if (variable != null) {
                        setters.push(variable);
                    }
                }
            },
            // Selector matching function calls like: setCount(1)
            'CallExpression[callee.type="Identifier"][arguments.length=1]'(node) {
                if (!isInsideFunctionScope(reactComponentScope, node) ||
                    setters.length === 0 ||
                    isInsideConditional(node)) {
                    return;
                }
                const maybeSetterCall = node;
                const calleeVariable = (0, ast_js_1.getVariableFromName)(context, maybeSetterCall.callee.name, node);
                if (calleeVariable && setters.includes(calleeVariable)) {
                    context.report({
                        messageId: 'noHookSetterInBody',
                        node: node.callee,
                    });
                }
            },
        };
    },
};
function isInsideConditional(node) {
    return ((0, ancestor_js_1.findFirstMatchingLocalAncestor)(node, n => n.type === 'IfStatement') !==
        undefined);
}
function hasParent(node) {
    return node.parent != null;
}
function matchesReactComponentName(node, max = 0) {
    if (node == null) {
        return false;
    }
    else if ((0, ast_js_1.isIdentifier)(node)) {
        return REACT_PATTERN.test(node.name);
    }
    else if (node.type === 'FunctionDeclaration') {
        return matchesReactComponentName(node.id);
    }
    else if (node.type === 'VariableDeclarator') {
        return matchesReactComponentName(node.id);
    }
    else if (node.type === 'AssignmentExpression') {
        return matchesReactComponentName(node.left);
    }
    else if (node.type === 'MemberExpression') {
        return matchesReactComponentName(node.property);
    }
    else if (hasParent(node) && max > 0) {
        return matchesReactComponentName(node.parent, max - 1);
    }
    else {
        return false;
    }
}
