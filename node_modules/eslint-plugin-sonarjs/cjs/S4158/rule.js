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
// https://sonarsource.github.io/rspec/#/rspec/S4158
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
const collection_js_1 = require("../helpers/collection.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
// Methods that mutate the collection but can't add elements
const nonAdditiveMutatorMethods = [
    // array methods
    'copyWithin',
    'pop',
    'reverse',
    'shift',
    'sort',
    // map, set methods
    'clear',
    'delete',
];
const accessorMethods = [
    // array methods
    'concat',
    'flat',
    'flatMap',
    'includes',
    'indexOf',
    'join',
    'lastIndexOf',
    'slice',
    'toSource',
    'toString',
    'toLocaleString',
    // map, set methods
    'get',
    'has',
];
const iterationMethods = [
    'entries',
    'every',
    'filter',
    'find',
    'findIndex',
    'forEach',
    'keys',
    'map',
    'reduce',
    'reduceRight',
    'some',
    'values',
];
const strictlyReadingMethods = new Set([
    ...nonAdditiveMutatorMethods,
    ...accessorMethods,
    ...iterationMethods,
]);
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            reviewUsageOfIdentifier: 'Review this usage of "{{identifierName}}" as it can only be empty here.',
        },
    }),
    create(context) {
        return {
            'Program:exit': (node) => {
                reportEmptyCollectionsUsage(context.sourceCode.getScope(node), context);
            },
        };
    },
};
function reportEmptyCollectionsUsage(scope, context) {
    if (scope.type !== 'global') {
        for (const v of scope.variables) {
            reportEmptyCollectionUsage(v, context);
        }
    }
    for (const childScope of scope.childScopes) {
        reportEmptyCollectionsUsage(childScope, context);
    }
}
function reportEmptyCollectionUsage(variable, context) {
    if (variable.references.length <= 1) {
        return;
    }
    if (variable.defs.some(d => d.type === 'Parameter' || d.type === 'ImportBinding')) {
        // Bound value initialized elsewhere, could be non-empty.
        return;
    }
    const readingUsages = [];
    let hasAssignmentOfEmptyCollection = false;
    for (const ref of variable.references) {
        if (ref.isWriteOnly()) {
            if (isReferenceAssigningEmptyCollection(ref)) {
                hasAssignmentOfEmptyCollection = true;
            }
            else {
                // There is at least one operation that might make the collection non-empty.
                // We ignore the order of usages, and consider all reads to be safe.
                return;
            }
        }
        else if (isReadingCollectionUsage(ref)) {
            readingUsages.push(ref);
        }
        else {
            // some unknown operation on the collection.
            // To avoid any FPs, we assume that it could make the collection non-empty.
            return;
        }
    }
    if (hasAssignmentOfEmptyCollection) {
        for (const ref of readingUsages) {
            context.report({
                messageId: 'reviewUsageOfIdentifier',
                data: {
                    identifierName: ref.identifier.name,
                },
                node: ref.identifier,
            });
        }
    }
}
function isReferenceAssigningEmptyCollection(ref) {
    const declOrExprStmt = (0, ancestor_js_1.findFirstMatchingAncestor)(ref.identifier, n => n.type === 'VariableDeclarator' || n.type === 'ExpressionStatement');
    if (declOrExprStmt) {
        if (declOrExprStmt.type === 'VariableDeclarator' && declOrExprStmt.init) {
            return isEmptyCollectionType(declOrExprStmt.init);
        }
        if (declOrExprStmt.type === 'ExpressionStatement') {
            const { expression } = declOrExprStmt;
            return (expression.type === 'AssignmentExpression' &&
                (0, ast_js_1.isReferenceTo)(ref, expression.left) &&
                isEmptyCollectionType(expression.right));
        }
    }
    return false;
}
function isEmptyCollectionType(node) {
    if (node?.type === 'ArrayExpression') {
        return node.elements.length === 0;
    }
    else if (node?.type === 'CallExpression' || node?.type === 'NewExpression') {
        return (0, ast_js_1.isIdentifier)(node.callee, ...collection_js_1.collectionConstructor) && node.arguments.length === 0;
    }
    return false;
}
function isReadingCollectionUsage(ref) {
    return isStrictlyReadingMethodCall(ref) || isForIterationPattern(ref) || isElementRead(ref);
}
function isStrictlyReadingMethodCall(usage) {
    const { parent } = usage.identifier;
    if (parent?.type === 'MemberExpression') {
        const memberExpressionParent = parent.parent;
        if (memberExpressionParent?.type === 'CallExpression') {
            return (0, ast_js_1.isIdentifier)(parent.property, ...strictlyReadingMethods);
        }
    }
    return false;
}
function isForIterationPattern(ref) {
    const forInOrOfStatement = (0, ancestor_js_1.findFirstMatchingAncestor)(ref.identifier, n => n.type === 'ForOfStatement' || n.type === 'ForInStatement');
    return forInOrOfStatement?.right === ref.identifier;
}
function isElementRead(ref) {
    const { parent } = ref.identifier;
    return (parent?.type === 'MemberExpression' &&
        parent.computed &&
        !isElementWrite(parent));
}
const writingAssignmentOperators = new Set(['=', '||=', '&&=', '??=']);
function isElementWrite(memberExpression) {
    const ancestors = (0, ancestor_js_1.ancestorsChain)(memberExpression, new Set());
    const assignment = ancestors.find(n => n.type === 'AssignmentExpression');
    if (assignment && writingAssignmentOperators.has(assignment.operator)) {
        return [memberExpression, ...ancestors].includes(assignment.left);
    }
    return false;
}
