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
// https://sonarsource.github.io/rspec/#/rspec/S1226/javascript
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
const ancestor_js_1 = require("../helpers/ancestor.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            noReassignment: 'Introduce a new variable or use its initial value before reassigning "{{reference}}".',
        },
    }),
    create(context) {
        let variableUsageContext = {
            type: 'global',
            variablesToCheckInCurrentScope: new Set(),
            variablesToCheck: new Set(),
            variablesRead: new Set(),
            referencesByIdentifier: new Map(),
        };
        function checkIdentifierUsage(identifier, identifierContextType) {
            if (variableUsageContext.type !== identifierContextType) {
                return;
            }
            const variableName = identifier.name;
            const currentReference = getReference(variableUsageContext, identifier);
            if (currentReference &&
                !currentReference.init &&
                !variableUsageContext.variablesRead.has(variableName)) {
                if (variableUsageContext.variablesToCheck.has(variableName) &&
                    currentReference.isWriteOnly() &&
                    !isUsedInWriteExpression(variableName, currentReference.writeExpr)) {
                    // we do not raise issue when value is reassigned inside a top-level IfStatement, as it might be a shift or
                    // default value reassignment
                    if (isInsideIfStatement(context, identifier) ||
                        context.sourceCode.getAncestors(identifier).some(node => node.type === 'SwitchCase') // issue-2398
                    ) {
                        return;
                    }
                    raiseIssue(currentReference);
                }
                markAsRead(variableUsageContext, variableName);
            }
            else if (variableName === 'arguments') {
                markAllFunctionArgumentsAsRead(variableUsageContext);
            }
        }
        function isUsedInWriteExpression(variableName, writeExpr) {
            return (writeExpr &&
                context.sourceCode.getFirstToken(writeExpr, token => token.value === variableName || token.value === 'arguments'));
        }
        function raiseIssue(reference) {
            const locationHolder = getPreciseLocationHolder(reference);
            context.report({
                messageId: 'noReassignment',
                data: {
                    reference: reference.identifier.name,
                },
                ...locationHolder,
            });
        }
        function popContext() {
            variableUsageContext = variableUsageContext.parentContext ?? variableUsageContext;
        }
        return {
            onCodePathStart(_codePath, node) {
                const currentScope = context.sourceCode.getScope(node);
                if (currentScope?.type === 'function') {
                    const { referencesByIdentifier, variablesToCheck, variablesToCheckInCurrentScope } = computeNewContextInfo(variableUsageContext, context, node);
                    const functionName = getFunctionName(node);
                    if (functionName) {
                        variablesToCheck.delete(functionName);
                    }
                    variableUsageContext = {
                        type: 'function',
                        parentContext: variableUsageContext,
                        variablesToCheck,
                        referencesByIdentifier,
                        variablesToCheckInCurrentScope,
                        variablesRead: computeSetDifference(variableUsageContext.variablesRead, variablesToCheckInCurrentScope),
                    };
                }
                else {
                    variableUsageContext = {
                        type: 'global',
                        parentContext: variableUsageContext,
                        variablesToCheckInCurrentScope: new Set(),
                        variablesToCheck: new Set(),
                        variablesRead: new Set(),
                        referencesByIdentifier: new Map(),
                    };
                }
            },
            onCodePathSegmentLoop(_fromSegment, _toSegment, node) {
                const parent = (0, ancestor_js_1.getParent)(context, node);
                if (!isForEachLoopStart(node, parent)) {
                    return;
                }
                const currentScope = context.sourceCode.scopeManager.acquire(parent.body);
                const { referencesByIdentifier, variablesToCheck, variablesToCheckInCurrentScope } = computeNewContextInfo(variableUsageContext, context, parent.left);
                if (currentScope) {
                    for (const ref of currentScope.references) {
                        referencesByIdentifier.set(ref.identifier, ref);
                    }
                }
                // In case of array or object pattern expression, the left hand side are not declared variables but simply identifiers
                for (const name of (0, ast_js_1.resolveIdentifiers)(parent.left, true).map(identifier => identifier.name)) {
                    variablesToCheck.add(name);
                    variablesToCheckInCurrentScope.add(name);
                }
                variableUsageContext = {
                    type: 'foreach',
                    parentContext: variableUsageContext,
                    variablesToCheckInCurrentScope,
                    variablesToCheck,
                    variablesRead: computeSetDifference(variableUsageContext.variablesRead, variablesToCheckInCurrentScope),
                    referencesByIdentifier,
                };
            },
            onCodePathSegmentStart(_segment, node) {
                if (node.type !== 'CatchClause') {
                    return;
                }
                const { referencesByIdentifier, variablesToCheck, variablesToCheckInCurrentScope } = computeNewContextInfo(variableUsageContext, context, node);
                variableUsageContext = {
                    type: 'catch',
                    parentContext: variableUsageContext,
                    variablesToCheckInCurrentScope,
                    variablesToCheck,
                    variablesRead: computeSetDifference(variableUsageContext.variablesRead, variablesToCheckInCurrentScope),
                    referencesByIdentifier,
                };
            },
            onCodePathEnd: popContext,
            'ForInStatement:exit': popContext,
            'ForOfStatement:exit': popContext,
            'CatchClause:exit': popContext,
            '*:function > BlockStatement Identifier': (node) => checkIdentifierUsage(node, 'function'),
            'ForInStatement > *:statement Identifier': (node) => checkIdentifierUsage(node, 'foreach'),
            'ForOfStatement > *:statement Identifier': (node) => checkIdentifierUsage(node, 'foreach'),
            'CatchClause > BlockStatement Identifier': (node) => checkIdentifierUsage(node, 'catch'),
        };
    },
};
function isInsideIfStatement(context, node) {
    const ancestors = context.sourceCode.getAncestors(node);
    for (let i = ancestors.length - 1; i >= 0; i--) {
        if (ancestors[i].type === 'IfStatement' &&
            // We check if the consequent or the alternate are also ancestors
            // Nodes in the test attribute should be raised
            i < ancestors.length - 1 &&
            (ancestors[i + 1] === ancestors[i].consequent ||
                ancestors[i + 1] === ancestors[i].alternate)) {
            return true;
        }
    }
    return false;
}
/**
 * Computes the set difference (a \ b)
 */
function computeSetDifference(a, b) {
    return new Set([...a].filter(str => !b.has(str)));
}
function getFunctionName(node) {
    return node.id ? node.id.name : null;
}
function isForEachLoopStart(node, parent) {
    return (node.type === 'BlockStatement' &&
        !!parent &&
        (parent.type === 'ForInStatement' || parent.type === 'ForOfStatement'));
}
function computeNewContextInfo(variableUsageContext, context, node) {
    const referencesByIdentifier = new Map();
    const variablesToCheck = new Set(variableUsageContext.variablesToCheck);
    const variablesToCheckInCurrentScope = new Set();
    for (const variable of context.sourceCode.getDeclaredVariables(node)) {
        variablesToCheck.add(variable.name);
        variablesToCheckInCurrentScope.add(variable.name);
        for (const currentRef of variable.references) {
            referencesByIdentifier.set(currentRef.identifier, currentRef);
        }
    }
    return { referencesByIdentifier, variablesToCheck, variablesToCheckInCurrentScope };
}
function markAsRead(context, variableName) {
    context.variablesRead.add(variableName);
    if (!context.variablesToCheckInCurrentScope.has(variableName) && context.parentContext) {
        markAsRead(context.parentContext, variableName);
    }
}
function markAllFunctionArgumentsAsRead(variableUsageContext) {
    let functionContext = variableUsageContext;
    while (functionContext && functionContext.type !== 'function') {
        functionContext = functionContext.parentContext;
    }
    if (functionContext) {
        for (const variableName of functionContext.variablesToCheckInCurrentScope) {
            functionContext.variablesRead.add(variableName);
        }
    }
}
function getPreciseLocationHolder(reference) {
    const identifierLoc = reference.identifier.loc;
    if (identifierLoc && reference.writeExpr?.loc) {
        return { loc: { start: identifierLoc.start, end: reference.writeExpr.loc.end } };
    }
    return { node: reference.identifier };
}
function getReference(variableUsageContext, identifier) {
    const identifierReference = variableUsageContext.referencesByIdentifier.get(identifier);
    if (!identifierReference && variableUsageContext.parentContext) {
        return getReference(variableUsageContext.parentContext, identifier);
    }
    return identifierReference;
}
