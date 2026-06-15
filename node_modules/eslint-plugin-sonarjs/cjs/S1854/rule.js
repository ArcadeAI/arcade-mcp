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
// https://sonarsource.github.io/rspec/#/rspec/S1854/javascript
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
const lva_js_1 = require("../helpers/lva.js");
const ancestor_js_1 = require("../helpers/ancestor.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const ast_js_1 = require("../helpers/ast.js");
const collection_js_1 = require("../helpers/collection.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            removeAssignment: 'Remove this useless assignment to variable "{{variable}}".',
        },
    }),
    create(context) {
        const codePathStack = [];
        const liveVariablesMap = new Map();
        const readVariables = new Set();
        // map from Variable to CodePath ids where variable is used
        const variableUsages = new Map();
        const referencesUsedInDestructuring = new Set();
        const destructuringStack = [];
        const codePathSegments = [];
        let currentCodePathSegments = [];
        // Variables that are written in try blocks and read in catch/finally blocks
        // These should not be reported as dead stores because exceptions can occur
        const variablesReadInCatch = new Set();
        return {
            ':matches(AssignmentExpression, VariableDeclarator[init])': (node) => {
                pushAssignmentContext(node);
            },
            ':matches(AssignmentExpression, VariableDeclarator[init]):exit': () => {
                popAssignmentContext();
            },
            Identifier: (node) => {
                if (isEnumConstant(node)) {
                    return;
                }
                checkIdentifierUsage(node);
            },
            JSXIdentifier: (node) => {
                checkIdentifierUsage(node);
            },
            ObjectPattern: () => {
                destructuringStack.push(new DestructuringContext());
            },
            'ObjectPattern > Property > Identifier': (node) => {
                const destructuring = (0, collection_js_1.last)(destructuringStack);
                const { ref } = resolveReference(node);
                if (ref) {
                    destructuring.references.push(ref);
                }
            },
            'ObjectPattern > :matches(RestElement, ExperimentalRestProperty)': () => {
                (0, collection_js_1.last)(destructuringStack).hasRest = true;
            },
            'ObjectPattern:exit': () => {
                const destructuring = destructuringStack.pop();
                if (destructuring?.hasRest) {
                    for (const ref of destructuring.references) {
                        referencesUsedInDestructuring.add(ref);
                    }
                }
            },
            TryStatement: (node) => {
                const tryStmt = node;
                collectVariablesReadInCatchOrFinally(tryStmt, context);
            },
            'Program:exit': () => {
                (0, lva_js_1.lva)(liveVariablesMap);
                for (const lva of liveVariablesMap.values()) {
                    checkSegment(lva);
                    reportNeverReadVariables(lva);
                }
            },
            // CodePath events
            onCodePathSegmentStart: (segment) => {
                liveVariablesMap.set(segment.id, new lva_js_1.LiveVariables(segment));
                currentCodePathSegments.push(segment);
            },
            onCodePathStart: codePath => {
                pushContext(new CodePathContext(codePath));
                codePathSegments.push(currentCodePathSegments);
                currentCodePathSegments = [];
            },
            onCodePathSegmentEnd() {
                currentCodePathSegments.pop();
            },
            onCodePathEnd: () => {
                popContext();
                currentCodePathSegments = codePathSegments.pop() || [];
            },
        };
        function pushAssignmentContext(node) {
            (0, collection_js_1.last)(codePathStack).assignmentStack.push(new AssignmentContext(node));
        }
        function popAssignmentContext() {
            const assignment = (0, collection_js_1.last)(codePathStack).assignmentStack.pop();
            for (const r of assignment.rhs) {
                processReference(r);
            }
            for (const r of assignment.lhs) {
                processReference(r);
            }
        }
        function checkSegment(liveVariables) {
            const willBeRead = new Set(liveVariables.out);
            const references = [...liveVariables.references].reverse();
            for (const ref of references) {
                const variable = ref.resolved;
                if (!variable) {
                    continue;
                }
                if (ref.isWrite()) {
                    if (!willBeRead.has(variable) && shouldReport(ref)) {
                        report(ref);
                    }
                    willBeRead.delete(variable);
                }
                if (ref.isRead()) {
                    willBeRead.add(variable);
                }
            }
        }
        function reportNeverReadVariables(lva) {
            for (const ref of lva.references) {
                if (shouldReportReference(ref) && !readVariables.has(ref.resolved)) {
                    report(ref);
                }
            }
        }
        function shouldReport(ref) {
            const variable = ref.resolved;
            return (variable &&
                shouldReportReference(ref) &&
                !variableUsedOutsideOfCodePath(variable) &&
                readVariables.has(variable));
        }
        function shouldReportReference(ref) {
            const variable = ref.resolved;
            return (variable &&
                isLocalVar(variable) &&
                !isReferenceWithBasicValue(ref) &&
                !isDefaultParameter(ref) &&
                !referencesUsedInDestructuring.has(ref) &&
                !variable.name.startsWith('_') &&
                !isIncrementOrDecrement(ref) &&
                !isNullAssignment(ref) &&
                !variablesReadInCatch.has(variable));
        }
        function isIncrementOrDecrement(ref) {
            const parent = ref.identifier.parent;
            return parent?.type === 'UpdateExpression';
        }
        function isNullAssignment(ref) {
            const parent = ref.identifier.parent;
            return parent?.type === 'AssignmentExpression' && (0, ast_js_1.isNullLiteral)(parent.right);
        }
        function isEnumConstant(node) {
            return context.sourceCode.getAncestors(node).some(n => n.type === 'TSEnumDeclaration');
        }
        function isDefaultParameter(ref) {
            if (ref.identifier.type !== 'Identifier') {
                return false;
            }
            const parent = ref.identifier.parent;
            return parent?.type === 'AssignmentPattern';
        }
        function isLocalVar(variable) {
            // @ts-ignore
            const scope = variable.scope;
            const node = scope.block;
            return node.type !== 'Program' && node.type !== 'TSModuleDeclaration';
        }
        function variableUsedOutsideOfCodePath(variable) {
            return variableUsages.get(variable).size > 1;
        }
        function isReferenceWithBasicValue(ref) {
            return ref.init && ref.writeExpr && isBasicValue(ref.writeExpr);
        }
        function report(ref) {
            context.report({
                messageId: 'removeAssignment',
                data: {
                    variable: ref.identifier.name,
                },
                loc: ref.identifier.loc,
            });
        }
        function checkIdentifierUsage(node) {
            const { ref, variable } = node.type === 'Identifier' ? resolveReference(node) : resolveJSXReference(node);
            if (ref) {
                processReference(ref);
                if (variable) {
                    updateReadVariables(ref);
                }
            }
            if (variable) {
                updateVariableUsages(variable);
            }
        }
        function resolveJSXReference(node) {
            if (isJSXAttributeName(node)) {
                return {};
            }
            const jsxReference = new JSXReference(node, context.sourceCode.getScope(node));
            return { ref: jsxReference, variable: jsxReference.resolved };
        }
        function processReference(ref) {
            const assignmentStack = (0, collection_js_1.last)(codePathStack).assignmentStack;
            if (assignmentStack.length > 0) {
                const assignment = (0, collection_js_1.last)(assignmentStack);
                assignment.add(ref);
            }
            else {
                for (const segment of currentCodePathSegments) {
                    lvaForSegment(segment).add(ref);
                }
            }
        }
        function lvaForSegment(segment) {
            let lva;
            if (liveVariablesMap.has(segment.id)) {
                lva = liveVariablesMap.get(segment.id);
            }
            else {
                lva = new lva_js_1.LiveVariables(segment);
                liveVariablesMap.set(segment.id, lva);
            }
            return lva;
        }
        function updateReadVariables(reference) {
            const variable = reference.resolved;
            if (reference.isRead()) {
                readVariables.add(variable);
            }
        }
        function updateVariableUsages(variable) {
            const codePathId = (0, collection_js_1.last)(codePathStack).codePath.id;
            if (variableUsages.has(variable)) {
                variableUsages.get(variable).add(codePathId);
            }
            else {
                variableUsages.set(variable, new Set([codePathId]));
            }
        }
        function popContext() {
            codePathStack.pop();
        }
        function pushContext(codePathContext) {
            codePathStack.push(codePathContext);
        }
        function resolveReference(node) {
            return resolveReferenceRecursively(node, context.sourceCode.getScope(node));
        }
        function resolveReferenceRecursively(node, scope, depth = 0) {
            if (scope === null || depth > 2) {
                return { ref: null, variable: null };
            }
            const ref = scope.references.find(r => r.identifier === node);
            if (ref) {
                return { ref, variable: ref.resolved };
            }
            else {
                // if it's not a reference, it can be just declaration without initializer
                const variable = scope.variables.find(v => v.defs.find(def => def.name === node));
                if (variable) {
                    return { ref: null, variable };
                }
                // we only need 1-level recursion, only for switch expression, which is likely a bug in eslint
                return resolveReferenceRecursively(node, scope.upper, depth + 1);
            }
        }
        /**
         * Collects variables that are read in catch or finally blocks.
         * Variables written in try and read in catch/finally should not be
         * reported as dead stores because an exception could occur between
         * assignments, making the earlier assignment value visible in the handler.
         */
        function collectVariablesReadInCatchOrFinally(tryStmt, ctx) {
            const handlerNodes = [];
            if (tryStmt.handler) {
                handlerNodes.push(tryStmt.handler.body);
            }
            if (tryStmt.finalizer) {
                handlerNodes.push(tryStmt.finalizer);
            }
            for (const handlerNode of handlerNodes) {
                // Get all identifier references in the catch/finally block
                visitIdentifiers(handlerNode, (identifier) => {
                    const scope = ctx.sourceCode.getScope(identifier);
                    const variable = findVariableInScope(scope, identifier.name);
                    if (variable && isDefinedOutsideTry(variable, tryStmt)) {
                        variablesReadInCatch.add(variable);
                    }
                });
            }
        }
        function visitIdentifiers(node, callback, visited = new Set()) {
            if (visited.has(node)) {
                return;
            }
            visited.add(node);
            if (node.type === 'Identifier') {
                callback(node);
                return;
            }
            for (const child of (0, ancestor_js_1.childrenOf)(node, context.sourceCode.visitorKeys)) {
                visitIdentifiers(child, callback, visited);
            }
        }
        function findVariableInScope(scope, name) {
            while (scope) {
                const variable = scope.variables.find(v => v.name === name);
                if (variable) {
                    return variable;
                }
                scope = scope.upper;
            }
            return null;
        }
    },
};
function isDefinedOutsideTry(variable, tryStmt) {
    return variable.defs.some(def => !isNodeInsideTryBlock(def.node, tryStmt));
}
function isNodeInsideTryBlock(node, tryStmt) {
    const tryBlock = tryStmt.block;
    const nodeRange = node.range;
    const tryRange = tryBlock.range;
    if (nodeRange && tryRange) {
        return nodeRange[0] >= tryRange[0] && nodeRange[1] <= tryRange[1];
    }
    return false;
}
class CodePathContext {
    constructor(codePath) {
        this.segments = new Map();
        this.assignmentStack = [];
        this.codePath = codePath;
    }
}
class DestructuringContext {
    constructor() {
        this.hasRest = false;
        this.references = [];
    }
}
class AssignmentContext {
    constructor(node) {
        this.lhs = new Set();
        this.rhs = new Set();
        this.node = node;
    }
    isRhs(node) {
        return this.node.type === 'AssignmentExpression'
            ? this.node.right === node
            : this.node.init === node;
    }
    isLhs(node) {
        return this.node.type === 'AssignmentExpression'
            ? this.node.left === node
            : this.node.id === node;
    }
    add(ref) {
        let parent = ref.identifier;
        while (parent) {
            if (this.isLhs(parent)) {
                this.lhs.add(ref);
                break;
            }
            if (this.isRhs(parent)) {
                this.rhs.add(ref);
                break;
            }
            parent = parent.parent;
        }
        if (parent === null) {
            throw new Error('failed to find assignment lhs/rhs');
        }
    }
}
class JSXReference {
    constructor(node, scope) {
        this.init = false;
        this.writeExpr = null;
        this.from = scope;
        this.identifier = node;
        this.resolved = findJSXVariableInScope(node, scope);
    }
    isRead() {
        return true;
    }
    isReadOnly() {
        return true;
    }
    isReadWrite() {
        return false;
    }
    isWrite() {
        return false;
    }
    isWriteOnly() {
        return false;
    }
}
function findJSXVariableInScope(node, scope) {
    return (scope &&
        (scope.variables.find(v => v.name === node.name) || findJSXVariableInScope(node, scope.upper)));
}
function isJSXAttributeName(node) {
    const parent = node.parent;
    return parent?.type === 'JSXAttribute' && parent.name === node;
}
function isBasicValue(node) {
    switch (node.type) {
        case 'Literal':
            return node.value === '' || [0, 1, null, true, false].includes(node.value);
        case 'Identifier':
            return node.name === 'undefined';
        case 'UnaryExpression':
            return isBasicValue(node.argument);
        case 'ObjectExpression':
            return node.properties.length === 0;
        case 'ArrayExpression':
            return node.elements.length === 0;
        default:
            return false;
    }
}
