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
// https://sonarsource.github.io/rspec/#/rspec/S2310/javascript
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
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        function checkLoop(updateNode, extractCounters, loopBody) {
            const counters = [];
            extractCounters(updateNode, counters);
            for (const counter of counters) {
                checkCounter(counter, loopBody);
            }
        }
        function checkCounter(counter, block) {
            const variable = (0, ast_js_1.getVariableFromName)(context, counter.name, block);
            if (!variable) {
                return;
            }
            for (const ref of variable.references) {
                if (ref.isWrite() && isUsedInsideBody(ref.identifier, block)) {
                    if (isIntentionalSkipAhead(ref.identifier, block)) {
                        continue;
                    }
                    (0, location_js_1.report)(context, {
                        node: ref.identifier,
                        message: `Remove this assignment of "${counter.name}".`,
                    }, [(0, location_js_1.toSecondaryLocation)(counter, 'Counter variable update')]);
                }
            }
        }
        return {
            'ForStatement > BlockStatement': (node) => {
                const forLoop = (0, ancestor_js_1.getParent)(context, node);
                if (forLoop.update) {
                    checkLoop(forLoop.update, collectCountersFor, node);
                }
            },
            // Note: for-of and for-in loops are not checked because reassigning
            // the iterator variable does not affect loop iteration (the iterator
            // protocol controls progression, not the variable value)
        };
    },
};
function collectCountersFor(updateExpression, counters) {
    let counter = undefined;
    if (updateExpression.type === 'AssignmentExpression') {
        counter = updateExpression.left;
    }
    else if (updateExpression.type === 'UpdateExpression') {
        counter = updateExpression.argument;
    }
    else if (updateExpression.type === 'SequenceExpression') {
        for (const e of updateExpression.expressions) {
            collectCountersFor(e, counters);
        }
    }
    if (counter?.type === 'Identifier') {
        counters.push(counter);
    }
}
/**
 * Checks if a loop counter modification is an intentional skip-ahead pattern
 * (UpdateExpression or compound assignment) rather than a simple assignment.
 * Simple assignments (=) are allowed when a splice() call using the same
 * counter variable exists in the enclosing block (splice compensation pattern).
 * Modifications in nested for-loop update clauses are not considered skip-ahead.
 */
function isIntentionalSkipAhead(id, outerLoopBody) {
    if (isInNestedForLoopUpdate(id, outerLoopBody)) {
        return false;
    }
    const parent = (0, ancestor_js_1.getNodeParent)(id);
    if (parent?.type === 'UpdateExpression') {
        return true;
    }
    if (parent?.type === 'AssignmentExpression' && parent.operator !== '=') {
        return true;
    }
    if (parent?.type === 'AssignmentExpression' && parent.operator === '=') {
        const block = findEnclosingBlock(id);
        if (block && blockContainsSpliceWithCounter(block, id.name)) {
            return true;
        }
    }
    return false;
}
/**
 * Walks up the AST from the given node to find the nearest enclosing BlockStatement.
 */
function findEnclosingBlock(node) {
    let current = (0, ancestor_js_1.getNodeParent)(node);
    while (current) {
        if (current.type === 'BlockStatement') {
            return current;
        }
        current = (0, ancestor_js_1.getNodeParent)(current);
    }
    return undefined;
}
/**
 * Checks whether a block contains a splice() call whose first argument
 * is an Identifier matching the given counter variable name.
 */
function blockContainsSpliceWithCounter(block, counterName) {
    return block.body.some(stmt => containsSpliceWithCounter(stmt, counterName));
}
/**
 * Checks whether a statement contains a splice() call whose first argument
 * references the given counter variable name. Only checks direct statements
 * in the block — not ones nested inside conditional branches.
 */
function containsSpliceWithCounter(node, counterName) {
    if (node.type === 'ExpressionStatement') {
        return expressionContainsSplice(node.expression, counterName);
    }
    if (node.type === 'VariableDeclaration' &&
        node.declarations.some(d => d.init?.type === 'CallExpression' && isSpliceCallWithCounter(d.init, counterName))) {
        return true;
    }
    return false;
}
/**
 * Checks whether an expression is or contains a splice() call whose first argument
 * matches the given counter variable name. Handles both direct splice calls
 * and splice calls on the right side of assignments (e.g., removed = arr.splice(i, 1)).
 */
function expressionContainsSplice(expr, counterName) {
    if (expr.type === 'CallExpression') {
        return isSpliceCallWithCounter(expr, counterName);
    }
    return (expr.type === 'AssignmentExpression' &&
        expr.right.type === 'CallExpression' &&
        isSpliceCallWithCounter(expr.right, counterName));
}
/**
 * Checks if a CallExpression is a .splice() call whose first argument
 * is an Identifier matching the counter variable name.
 */
function isSpliceCallWithCounter(call, counterName) {
    return (call.callee.type === 'MemberExpression' &&
        call.callee.property.type === 'Identifier' &&
        call.callee.property.name === 'splice' &&
        call.arguments.length >= 1 &&
        call.arguments[0].type === 'Identifier' &&
        call.arguments[0].name === counterName);
}
function isUsedInsideBody(id, loopBody) {
    const bodyRange = loopBody.range;
    return id.range && bodyRange && id.range[0] > bodyRange[0] && id.range[1] < bodyRange[1];
}
function isInNestedForLoopUpdate(id, outerLoopBody) {
    let node = id;
    let parent = (0, ancestor_js_1.getNodeParent)(node);
    while (parent) {
        // Stop if we've reached the outer loop body
        if (parent === outerLoopBody) {
            return false;
        }
        // Check if we're in a nested for-loop's update clause
        if (parent.type === 'ForStatement' && parent.update) {
            const updateRange = parent.update.range;
            if (updateRange &&
                id.range &&
                id.range[0] >= updateRange[0] &&
                id.range[1] <= updateRange[1]) {
                return true;
            }
        }
        node = parent;
        parent = (0, ancestor_js_1.getNodeParent)(node);
    }
    return false;
}
