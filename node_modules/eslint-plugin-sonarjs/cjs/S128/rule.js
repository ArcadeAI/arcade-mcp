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
// https://sonarsource.github.io/rspec/#/rspec/S128/javascript
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
            switchEnd: 'End this switch case with an unconditional break, continue, return or throw statement.',
        },
    }),
    create(context) {
        let currentCodeSegment = null;
        let enteringSwitchCase = false;
        let currentSegments = new Set();
        const allCurrentSegments = [];
        const segmentsWithExit = new Set();
        const initialSegmentBySwitchCase = new Map();
        const switchCaseStack = [];
        function noComment(node) {
            return context.sourceCode.getCommentsAfter(node).length === 0;
        }
        function isAfterProcessExitCall(segment, initialSegment) {
            const stack = [];
            const visitedSegments = new Set();
            stack.push(segment);
            while (stack.length !== 0) {
                const current = stack.pop();
                visitedSegments.add(current.id);
                if (!segmentsWithExit.has(current.id)) {
                    if (current === initialSegment) {
                        return false;
                    }
                    for (const codePathSegment of current.prevSegments.filter(p => !visitedSegments.has(p.id))) {
                        stack.push(codePathSegment);
                    }
                }
            }
            return true;
        }
        return {
            onCodePathStart() {
                allCurrentSegments.push(currentSegments);
                currentSegments = new Set();
            },
            onCodePathEnd() {
                currentSegments = allCurrentSegments.pop();
            },
            onCodePathSegmentStart(segment) {
                currentSegments.add(segment);
                currentCodeSegment = segment;
                if (enteringSwitchCase) {
                    initialSegmentBySwitchCase.set(switchCaseStack.pop(), currentCodeSegment);
                    enteringSwitchCase = false;
                }
            },
            onCodePathSegmentEnd(segment) {
                currentSegments.delete(segment);
            },
            onUnreachableCodePathSegmentStart(segment) {
                currentSegments.add(segment);
            },
            onUnreachableCodePathSegmentEnd(segment) {
                currentSegments.delete(segment);
            },
            CallExpression(node) {
                const callExpr = node;
                if (isProcessExitCall(callExpr)) {
                    segmentsWithExit.add(currentCodeSegment.id);
                }
            },
            SwitchCase(node) {
                enteringSwitchCase = true;
                switchCaseStack.push(node);
            },
            'SwitchCase:exit'(node) {
                const switchCase = node;
                const initialSegment = initialSegmentBySwitchCase.get(switchCase);
                const isReachable = Array.from(currentSegments).some(s => s.reachable && !isAfterProcessExitCall(s, initialSegment));
                const { cases } = (0, ancestor_js_1.getParent)(context, node);
                if (isReachable &&
                    switchCase.consequent.length > 0 &&
                    cases.at(-1) !== node &&
                    noComment(switchCase)) {
                    context.report({
                        messageId: 'switchEnd',
                        loc: context.sourceCode.getFirstToken(node).loc,
                    });
                }
            },
        };
    },
};
function isProcessExitCall(callExpr) {
    return (callExpr.callee.type === 'MemberExpression' &&
        callExpr.callee.object.type === 'Identifier' &&
        callExpr.callee.object.name === 'process' &&
        callExpr.callee.property.type === 'Identifier' &&
        callExpr.callee.property.name === 'exit');
}
