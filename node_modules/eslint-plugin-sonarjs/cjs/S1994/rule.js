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
// https://sonarsource.github.io/rspec/#/rspec/S1994/javascript
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
const equivalence_js_1 = require("../helpers/equivalence.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const ancestor_js_1 = require("../helpers/ancestor.js");
const collection_js_1 = require("../helpers/collection.js");
const meta = __importStar(require("./generated-meta.js"));
class ForInfo {
    constructor(forLoop) {
        this.forLoop = forLoop;
        this.updatedExpressions = [];
        this.testedExpressions = [];
    }
}
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            misplacedCounter: `This loop's stop condition tests "{{test}}" but the incrementer updates "{{update}}".`,
        },
    }),
    create(context) {
        const forLoopStack = [];
        function join(expressions) {
            return expressions.map(expr => context.sourceCode.getText(expr)).join(', ');
        }
        function isInsideUpdate(node) {
            return isInside(node, f => f.update);
        }
        function isInsideTest(node) {
            return isInside(node, f => f.test);
        }
        function isInside(node, getChild) {
            if (forLoopStack.length > 0) {
                const currentLoop = peekFor();
                const parentChain = context.sourceCode.getAncestors(node);
                parentChain.push(node);
                const forLoopChild = getChild(currentLoop.forLoop);
                if (forLoopChild) {
                    return parentChain.includes(forLoopChild);
                }
            }
            return false;
        }
        function peekFor() {
            return (0, collection_js_1.last)(forLoopStack);
        }
        return {
            ForStatement: (node) => {
                forLoopStack.push(new ForInfo(node));
            },
            'ForStatement:exit': () => {
                const forInfo = forLoopStack.pop();
                if (forInfo.updatedExpressions.length === 0 || !forInfo.forLoop.test) {
                    return;
                }
                const hasIntersection = forInfo.testedExpressions.some(testedExpr => forInfo.updatedExpressions.some(updatedExpr => (0, equivalence_js_1.areEquivalent)(updatedExpr, testedExpr, context.sourceCode)));
                if (!hasIntersection) {
                    context.report({
                        loc: context.sourceCode.getFirstToken(forInfo.forLoop).loc,
                        messageId: 'misplacedCounter',
                        data: {
                            test: join(forInfo.testedExpressions),
                            update: join(forInfo.updatedExpressions),
                        },
                    });
                }
            },
            'ForStatement AssignmentExpression': (node) => {
                if (isInsideUpdate(node)) {
                    const left = node.left;
                    const assignedExpressions = [];
                    computeAssignedExpressions(left, assignedExpressions);
                    const { updatedExpressions } = peekFor();
                    for (const ass of assignedExpressions) {
                        updatedExpressions.push(ass);
                    }
                }
            },
            'ForStatement UpdateExpression': (node) => {
                if (isInsideUpdate(node)) {
                    peekFor().updatedExpressions.push(node.argument);
                }
            },
            'ForStatement CallExpression': (node) => {
                if (!isInsideUpdate(node)) {
                    return;
                }
                const callee = getCalleeObject(node);
                if (callee) {
                    peekFor().updatedExpressions.push(callee);
                }
            },
            'ForStatement Identifier': (node) => {
                if (isInsideTest(node)) {
                    const parent = (0, ancestor_js_1.getParent)(context, node);
                    if (parent.type !== 'MemberExpression' || parent.computed || parent.object === node) {
                        peekFor().testedExpressions.push(node);
                    }
                }
            },
            'ForStatement MemberExpression': (node) => {
                if (isInsideTest(node) &&
                    (0, ancestor_js_1.getParent)(context, node).type !== 'MemberExpression' &&
                    (0, ancestor_js_1.getParent)(context, node).type !== 'CallExpression') {
                    peekFor().testedExpressions.push(node);
                }
            },
        };
    },
};
function getCalleeObject(node) {
    let callee = node.callee;
    while (callee.type === 'MemberExpression') {
        callee = callee.object;
    }
    if (callee.type === 'Identifier' && callee !== node.callee) {
        return callee;
    }
    return null;
}
function computeAssignedExpressions(node, assigned) {
    switch (node?.type) {
        case 'ArrayPattern':
            for (const element of node.elements) {
                computeAssignedExpressions(element, assigned);
            }
            break;
        case 'ObjectPattern':
            for (const property of node.properties) {
                computeAssignedExpressions(property, assigned);
            }
            break;
        case 'Property':
            computeAssignedExpressions(node.value, assigned);
            break;
        case 'AssignmentPattern':
            computeAssignedExpressions(node.left, assigned);
            break;
        default:
            assigned.push(node);
    }
}
