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
// https://sonarsource.github.io/rspec/#/rspec/S4165/javascript
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
const reaching_definitions_js_1 = require("../helpers/reaching-definitions.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const collection_js_1 = require("../helpers/collection.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            reviewAssignment: 'Review this redundant assignment: "{{symbol}}" already holds the assigned value along all execution paths.',
        },
    }),
    create(context) {
        const codePathStack = [];
        const reachingDefsMap = new Map();
        // map from Variable to CodePath ids where variable is used
        const variableUsages = new Map();
        const codePathSegments = [];
        let currentCodePathSegments = [];
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
            'Program:exit': () => {
                (0, reaching_definitions_js_1.reachingDefinitions)(reachingDefsMap);
                for (const defs of reachingDefsMap.values()) {
                    checkSegment(defs);
                }
                reachingDefsMap.clear();
                variableUsages.clear();
                while (codePathStack.length > 0) {
                    codePathStack.pop();
                }
            },
            // CodePath events
            onCodePathSegmentStart: (segment) => {
                reachingDefsMap.set(segment.id, new reaching_definitions_js_1.ReachingDefinitions(segment));
                currentCodePathSegments.push(segment);
            },
            onCodePathStart: codePath => {
                pushContext(new CodePathContext(codePath));
                codePathSegments.push(currentCodePathSegments);
                currentCodePathSegments = [];
            },
            onCodePathEnd: () => {
                popContext();
                currentCodePathSegments = codePathSegments.pop() || [];
            },
            onCodePathSegmentEnd() {
                currentCodePathSegments.pop();
            },
        };
        function popAssignmentContext() {
            const assignment = (0, collection_js_1.last)(codePathStack).assignmentStack.pop();
            for (const r of assignment.rhs) {
                processReference(r);
            }
            for (const r of assignment.lhs) {
                processReference(r);
            }
        }
        function pushAssignmentContext(node) {
            (0, collection_js_1.last)(codePathStack).assignmentStack.push(new AssignmentContext(node));
        }
        function checkSegment(reachingDefs) {
            const assignedValuesMap = new Map(reachingDefs.in);
            for (const ref of reachingDefs.references) {
                const variable = ref.resolved;
                if (!variable || !ref.isWrite() || !shouldReport(ref)) {
                    continue;
                }
                const lhsValues = assignedValuesMap.get(variable);
                const rhsValues = (0, reaching_definitions_js_1.resolveAssignedValues)(variable, ref.writeExpr, assignedValuesMap, ref.from);
                if (lhsValues?.type === 'AssignedValues' && lhsValues?.size === 1) {
                    const [lhsVal] = [...lhsValues];
                    checkRedundantAssignement(ref, ref.writeExpr, lhsVal, rhsValues, variable.name);
                }
                assignedValuesMap.set(variable, rhsValues);
            }
        }
        function checkRedundantAssignement({ resolved: variable }, node, lhsVal, rhsValues, name) {
            if (rhsValues.type === 'UnknownValue' || rhsValues.size !== 1) {
                return;
            }
            const [rhsVal] = [...rhsValues];
            if (!isWrittenOnlyOnce(variable) && lhsVal === rhsVal) {
                context.report({
                    node: node,
                    messageId: 'reviewAssignment',
                    data: {
                        symbol: name,
                    },
                });
            }
        }
        // to avoid raising on code like:
        // while (cond) {  let x = 42; }
        function isWrittenOnlyOnce(variable) {
            return variable.references.filter(ref => ref.isWrite()).length === 1;
        }
        function shouldReport(ref) {
            const variable = ref.resolved;
            return variable && shouldReportReference(ref) && !variableUsedOutsideOfCodePath(variable);
        }
        function shouldReportReference(ref) {
            const variable = ref.resolved;
            return (variable &&
                !isDefaultParameter(ref) &&
                !variable.name.startsWith('_') &&
                !isCompoundAssignment(ref.writeExpr) &&
                !isSelfAssignement(ref) &&
                !isInForLoopInit(ref) &&
                !isDeclarationInsideLoopBody(ref) &&
                !variable.defs.some(def => def.type === 'Parameter' || (def.type === 'Variable' && !def.node.init)));
        }
        function isEnumConstant(node) {
            return context.sourceCode.getAncestors(node).some(n => n.type === 'TSEnumDeclaration');
        }
        function variableUsedOutsideOfCodePath(variable) {
            return variableUsages.get(variable).size > 1;
        }
        function checkIdentifierUsage(node) {
            const { ref, variable } = resolveReference(node);
            if (ref) {
                processReference(ref);
            }
            if (variable) {
                updateVariableUsages(variable);
            }
        }
        function processReference(ref) {
            const assignmentStack = (0, collection_js_1.last)(codePathStack).assignmentStack;
            if (assignmentStack.length > 0) {
                const assignment = (0, collection_js_1.last)(assignmentStack);
                assignment.add(ref);
            }
            else {
                for (const segment of currentCodePathSegments) {
                    const reachingDefs = reachingDefsForSegment(segment);
                    reachingDefs.add(ref);
                }
            }
        }
        function reachingDefsForSegment(segment) {
            let defs;
            if (reachingDefsMap.has(segment.id)) {
                defs = reachingDefsMap.get(segment.id);
            }
            else {
                defs = new reaching_definitions_js_1.ReachingDefinitions(segment);
                reachingDefsMap.set(segment.id, defs);
            }
            return defs;
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
        function pushContext(codePathContext) {
            codePathStack.push(codePathContext);
        }
        function popContext() {
            codePathStack.pop();
        }
        function resolveReferenceRecursively(node, scope) {
            if (scope === null) {
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
                // in theory we only need 1-level recursion, only for switch expression, which is likely a bug in eslint
                // generic recursion is used for safety & readability
                return resolveReferenceRecursively(node, scope.upper);
            }
        }
        function resolveReference(node) {
            return resolveReferenceRecursively(node, context.sourceCode.getScope(node));
        }
    },
};
class CodePathContext {
    constructor(codePath) {
        this.reachingDefinitionsMap = new Map();
        this.reachingDefinitionsStack = [];
        this.segments = new Map();
        this.assignmentStack = [];
        this.codePath = codePath;
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
function isSelfAssignement(ref) {
    const lhs = ref.resolved;
    if (ref.writeExpr?.type === 'Identifier') {
        const rhs = (0, reaching_definitions_js_1.getVariableFromIdentifier)(ref.writeExpr, ref.from);
        return lhs === rhs;
    }
    return false;
}
function isCompoundAssignment(writeExpr) {
    if (writeExpr?.hasOwnProperty('parent')) {
        const node = writeExpr.parent;
        return node?.type === 'AssignmentExpression' && node.operator !== '=';
    }
    return false;
}
function isDefaultParameter(ref) {
    if (ref.identifier.type !== 'Identifier') {
        return false;
    }
    const parent = ref.identifier.parent;
    return parent?.type === 'AssignmentPattern';
}
/**
 * Checks if an assignment is part of a for-loop initialization.
 * For-loop initializations (e.g., `for (i = 0; ...)`) are idiomatic patterns
 * that should not be flagged as redundant, even if the variable already holds
 * the same value.
 */
function isInForLoopInit(ref) {
    const writeExpr = ref.writeExpr;
    if (!writeExpr) {
        return false;
    }
    let current = writeExpr;
    while (current) {
        const parent = current.parent;
        if (!parent) {
            break;
        }
        if (parent.type === 'ForStatement' && parent.init === current) {
            return true;
        }
        // Stop at function boundaries
        if (parent.type === 'FunctionDeclaration' ||
            parent.type === 'FunctionExpression' ||
            parent.type === 'ArrowFunctionExpression') {
            break;
        }
        current = parent;
    }
    return false;
}
/**
 * Checks if a variable declaration with initialization is inside a loop body.
 * Variable declarations inside loop bodies (e.g., `while (cond) { var x = 0; }`)
 * should not be flagged as redundant because each iteration reinitializes the variable.
 * For `let`/`const`, each iteration creates a new binding.
 * For `var`, the initialization still runs each iteration and is idiomatic.
 */
function isDeclarationInsideLoopBody(ref) {
    const variable = ref.resolved;
    if (!variable) {
        return false;
    }
    // Find the variable declaration that corresponds to this write reference
    const varDef = variable.defs.find(def => def.type === 'Variable' && def.node.init && def.name === ref.identifier);
    if (!varDef) {
        return false;
    }
    // Get the VariableDeclaration node (parent of VariableDeclarator)
    const varDeclarator = varDef.node;
    const varDeclaration = varDeclarator.parent;
    if (varDeclaration?.type !== 'VariableDeclaration') {
        return false;
    }
    // Traverse up to find if this declaration is inside a loop body
    let current = varDeclaration;
    while (current) {
        const parent = current.parent;
        if (!parent) {
            break;
        }
        // Check if we're inside a loop body
        if ((parent.type === 'ForStatement' && parent.body === current) ||
            (parent.type === 'ForInStatement' && parent.body === current) ||
            (parent.type === 'ForOfStatement' && parent.body === current) ||
            (parent.type === 'WhileStatement' && parent.body === current) ||
            (parent.type === 'DoWhileStatement' && parent.body === current)) {
            return true;
        }
        // Stop at function boundaries
        if (parent.type === 'FunctionDeclaration' ||
            parent.type === 'FunctionExpression' ||
            parent.type === 'ArrowFunctionExpression') {
            break;
        }
        current = parent;
    }
    return false;
}
