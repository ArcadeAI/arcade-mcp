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
// https://sonarsource.github.io/rspec/#/rspec/S4030
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
const collection_js_1 = require("../helpers/collection.js");
const ancestor_js_1 = require("../helpers/ancestor.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            unusedCollection: "Either use this collection's contents or remove the collection.",
        },
    }),
    create(context) {
        return {
            'Program:exit': (node) => {
                const unusedArrays = [];
                collectUnusedCollections(context.sourceCode.getScope(node), unusedArrays);
                for (const unusedArray of unusedArrays) {
                    context.report({
                        messageId: 'unusedCollection',
                        node: unusedArray.identifiers[0],
                    });
                }
            },
        };
    },
};
function collectUnusedCollections(scope, unusedArray) {
    if (scope.type !== 'global') {
        for (const v of scope.variables.filter(isUnusedCollection)) {
            unusedArray.push(v);
        }
    }
    for (const childScope of scope.childScopes) {
        collectUnusedCollections(childScope, unusedArray);
    }
}
function isExported(variable) {
    const definition = variable.defs[0];
    return definition && definition.node.parent?.parent?.type.startsWith('Export');
}
function isUnusedCollection(variable) {
    if (isExported(variable)) {
        return false;
    }
    if (variable.references.length <= 1) {
        return false;
    }
    let assignCollection = false;
    for (const ref of variable.references) {
        if (ref.isWriteOnly()) {
            if (isReferenceAssigningCollection(ref)) {
                assignCollection = true;
            }
            else {
                //One assignment is not a collection, we don't go further
                return false;
            }
        }
        else if (isRead(ref)) {
            //Unfortunately, isRead (!isWrite) from Scope.Reference consider A[1] = 1; and A.xxx(); as a read operation, we need to filter further
            return false;
        }
    }
    return assignCollection;
}
function isReferenceAssigningCollection(ref) {
    const declOrExprStmt = (0, ancestor_js_1.findFirstMatchingAncestor)(ref.identifier, n => n.type === 'VariableDeclarator' || n.type === 'ExpressionStatement');
    if (declOrExprStmt) {
        if (declOrExprStmt.type === 'VariableDeclarator' && declOrExprStmt.init) {
            return isCollectionType(declOrExprStmt.init);
        }
        if (declOrExprStmt.type === 'ExpressionStatement') {
            const { expression } = declOrExprStmt;
            return (expression?.type === 'AssignmentExpression' &&
                isReferenceTo(ref, expression.left) &&
                isCollectionType(expression.right));
        }
    }
    return false;
}
function isCollectionType(node) {
    if (node?.type === 'ArrayExpression') {
        return true;
    }
    else if (node?.type === 'CallExpression' || node?.type === 'NewExpression') {
        return (0, ast_js_1.isIdentifier)(node.callee, ...collection_js_1.collectionConstructor);
    }
    return false;
}
function isRead(ref) {
    const expressionStatement = (0, ancestor_js_1.findFirstMatchingAncestor)(ref.identifier, n => n.type === 'ExpressionStatement');
    if (expressionStatement) {
        return !((0, ast_js_1.isElementWrite)(expressionStatement, ref, false) ||
            isWritingMethodCall(expressionStatement, ref));
    }
    //All the write statement that we search are part of ExpressionStatement, if there is none, it's a read
    return true;
}
/**
 * Detect expression statements like the following:
 * myArray.push(1);
 */
function isWritingMethodCall(statement, ref) {
    if (statement.expression?.type === 'CallExpression') {
        const { callee } = statement.expression;
        if (callee.type === 'MemberExpression') {
            const { property } = callee;
            return isReferenceTo(ref, callee.object) && (0, ast_js_1.isIdentifier)(property, ...collection_js_1.writingMethods);
        }
    }
    return false;
}
function isReferenceTo(ref, node) {
    return node.type === 'Identifier' && node === ref.identifier;
}
