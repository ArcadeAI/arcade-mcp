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
// https://sonarsource.github.io/rspec/#/rspec/S1121/javascript
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
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            extractAssignment: 'Extract the assignment of "{{symbol}}" from this expression.',
        },
    }),
    create(context) {
        return {
            AssignmentExpression: (node) => {
                const assignment = node;
                const parent = (0, ancestor_js_1.getParent)(context, node);
                if (parent &&
                    !isAssignmentStatement(parent) &&
                    !isEnclosingChain(parent) &&
                    !isEnclosingRelation(parent) &&
                    !isEnclosingSequence(parent) &&
                    !isEnclosingDeclarator(parent) &&
                    !isLambdaBody(parent, assignment) &&
                    !isConditionalAssignment(parent, assignment) &&
                    !isWhileCondition(parent, assignment) &&
                    !isForInitOrUpdate(parent, assignment)) {
                    raiseIssue(assignment, context);
                }
            },
        };
    },
};
function raiseIssue(node, context) {
    const sourceCode = context.sourceCode;
    const operator = sourceCode.getFirstTokenBetween(node.left, node.right, token => token.value === node.operator);
    const text = sourceCode.getText(node.left);
    context.report({
        messageId: 'extractAssignment',
        data: {
            symbol: text,
        },
        loc: operator.loc,
    });
}
function isAssignmentStatement(parent) {
    return parent.type === 'ExpressionStatement';
}
function isEnclosingChain(parent) {
    return parent.type === 'AssignmentExpression';
}
function isEnclosingRelation(parent) {
    return (parent.type === 'BinaryExpression' &&
        ['==', '!=', '===', '!==', '<', '<=', '>', '>='].includes(parent.operator));
}
function isEnclosingSequence(parent) {
    return parent.type === 'SequenceExpression';
}
function isEnclosingDeclarator(parent) {
    return parent.type === 'VariableDeclarator';
}
function isLambdaBody(parent, expr) {
    return parent.type === 'ArrowFunctionExpression' && parent.body === expr;
}
function isConditionalAssignment(parent, expr) {
    return parent.type === 'LogicalExpression' && parent.right === expr;
}
function isWhileCondition(parent, expr) {
    return ((parent.type === 'DoWhileStatement' || parent.type === 'WhileStatement') && parent.test === expr);
}
function isForInitOrUpdate(parent, expr) {
    return parent.type === 'ForStatement' && (parent.init === expr || parent.update === expr);
}
