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
// https://sonarsource.github.io/rspec/#/rspec/S1515/javascript
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
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
const message = 'Make sure this function is not called after the loop completes.';
const loopLike = 'WhileStatement,DoWhileStatement,ForStatement,ForOfStatement,ForInStatement';
const functionLike = 'FunctionDeclaration,FunctionExpression,ArrowFunctionExpression';
const allowedCallbacks = new Set([
    'replace',
    'forEach',
    'filter',
    'map',
    'find',
    'findIndex',
    'every',
    'some',
    'reduce',
    'reduceRight',
    'sort',
    'each',
]);
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        return {
            [functionLike]: (node) => {
                const loopNode = getLocalEnclosingLoop(node);
                if (loopNode &&
                    !isIIFE(node, context) &&
                    !isAllowedCallbacks(context, node) &&
                    context.sourceCode.getScope(node).through.some(ref => !isSafe(ref, loopNode))) {
                    (0, location_js_1.report)(context, {
                        message,
                        loc: (0, location_js_1.getMainFunctionTokenLocation)(node, (0, ancestor_js_1.getParent)(context, node), context),
                    }, [(0, location_js_1.toSecondaryLocation)(getMainLoopToken(loopNode, context))]);
                }
            },
        };
    },
};
function getLocalEnclosingLoop(node) {
    return (0, ancestor_js_1.findFirstMatchingAncestor)(node, n => loopLike.includes(n.type));
}
function isIIFE(node, context) {
    const parent = (0, ancestor_js_1.getParent)(context, node);
    return (parent &&
        ((parent.type === 'CallExpression' && parent.callee === node) ||
            (parent.type === 'MemberExpression' && parent.object === node)));
}
function isAllowedCallbacks(context, node) {
    const parent = (0, ancestor_js_1.getParent)(context, node);
    if (parent?.type === 'CallExpression') {
        const callee = parent.callee;
        if (callee.type === 'MemberExpression') {
            return callee.property.type === 'Identifier' && allowedCallbacks.has(callee.property.name);
        }
    }
    return false;
}
function isSafe(ref, loopNode) {
    const variable = ref.resolved;
    if (variable) {
        const definition = variable.defs[0];
        const declaration = definition?.parent;
        const kind = declaration?.type === 'VariableDeclaration' ? declaration.kind : '';
        if (kind !== 'let' && kind !== 'const') {
            return hasConstValue(variable, loopNode);
        }
    }
    return true;
}
function hasConstValue(variable, loopNode) {
    for (const ref of variable.references) {
        if (ref.isWrite()) {
            //Check if write is in the scope of the loop
            if (ref.from.type === 'block' && ref.from.block === loopNode.body) {
                return false;
            }
            const refRange = ref.identifier.range;
            const range = getLoopTestRange(loopNode);
            //Check if value change in the header of the loop
            if (refRange && range && refRange[0] >= range[0] && refRange[1] <= range[1]) {
                return false;
            }
        }
    }
    return true;
}
function getLoopTestRange(loopNode) {
    const bodyRange = loopNode.body.range;
    if (bodyRange) {
        switch (loopNode.type) {
            case 'ForStatement':
                if (loopNode.test?.range) {
                    return [loopNode.test.range[0], bodyRange[0]];
                }
                break;
            case 'WhileStatement':
            case 'DoWhileStatement':
                return loopNode.test.range;
            case 'ForOfStatement':
            case 'ForInStatement': {
                const leftRange = loopNode.range;
                if (leftRange) {
                    return [leftRange[0], bodyRange[0]];
                }
            }
        }
    }
    return undefined;
}
function getMainLoopToken(loop, context) {
    const sourceCode = context.sourceCode;
    let token;
    switch (loop.type) {
        case 'WhileStatement':
        case 'DoWhileStatement':
            token = sourceCode.getTokenBefore(loop.test, t => t.type === 'Keyword' && t.value === 'while');
            break;
        case 'ForStatement':
        case 'ForOfStatement':
        default:
            token = sourceCode.getFirstToken(loop, t => t.type === 'Keyword' && t.value === 'for');
    }
    return token;
}
