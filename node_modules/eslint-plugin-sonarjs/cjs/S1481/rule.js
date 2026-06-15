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
// https://sonarsource.github.io/rspec/#/rspec/S1481/javascript
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
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            unusedFunction: `Remove unused function '{{symbol}}'.`,
            unusedVariable: `Remove the declaration of the unused '{{symbol}}' variable.`,
        },
    }),
    create(context) {
        let toIgnore = [];
        let jsxComponentsToIgnore = [];
        function checkVariable(v, toCheck) {
            if (v.defs.length === 0) {
                return;
            }
            const type = v.defs[0].type;
            if (type !== 'Variable' && type !== 'FunctionName') {
                return;
            }
            if (toCheck === 'let-const-function') {
                const def = v.defs[0];
                if (def.parent?.type === 'VariableDeclaration' && def.parent.kind === 'var') {
                    return;
                }
            }
            const defs = v.defs.map(def => def.name);
            const unused = v.references.every(ref => defs.includes(ref.identifier));
            if (unused && !toIgnore.includes(defs[0]) && !jsxComponentsToIgnore.includes(v.name)) {
                const messageAndData = type === 'FunctionName'
                    ? getUnusedFunctionMessageAndData(v.name)
                    : getUnusedVariableMessageAndData(v.name);
                for (const def of defs) {
                    context.report({
                        node: def,
                        ...messageAndData,
                    });
                }
            }
        }
        function checkScope(scope, checkedInParent) {
            let toCheck = checkedInParent;
            if (scope.type === 'function' && !isParentOfModuleScope(scope)) {
                toCheck = 'all';
            }
            else if (checkedInParent === 'nothing' && scope.type === 'block') {
                toCheck = 'let-const-function';
            }
            if (toCheck !== 'nothing' && scope.type !== 'function-expression-name') {
                for (const v of scope.variables) {
                    checkVariable(v, toCheck);
                }
            }
            for (const childScope of scope.childScopes) {
                checkScope(childScope, toCheck);
            }
        }
        return {
            ObjectPattern: (node) => {
                const elements = node.properties;
                const hasRest = elements.some(element => element.type === 'RestElement');
                if (!hasRest) {
                    return;
                }
                for (const element of elements) {
                    if (element.type === 'Property' &&
                        element.shorthand &&
                        element.value.type === 'Identifier') {
                        toIgnore.push(element.value);
                    }
                }
            },
            JSXIdentifier: (node) => {
                // using 'any' as standard typings for AST don't provide types for JSX
                jsxComponentsToIgnore.push(node.name);
            },
            'Program:exit': (node) => {
                checkScope(context.sourceCode.getScope(node), 'nothing');
                toIgnore = [];
                jsxComponentsToIgnore = [];
            },
        };
    },
};
function isParentOfModuleScope(scope) {
    return scope.childScopes.some(s => s.type === 'module');
}
function getUnusedFunctionMessageAndData(name) {
    return { messageId: 'unusedFunction', data: { symbol: name } };
}
function getUnusedVariableMessageAndData(name) {
    return { messageId: 'unusedVariable', data: { symbol: name } };
}
