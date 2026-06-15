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
// https://sonarsource.github.io/rspec/#/rspec/S1119/javascript
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
const meta = __importStar(require("./generated-meta.js"));
const LOOP_TYPES = new Set([
    'ForStatement',
    'WhileStatement',
    'DoWhileStatement',
    'ForInStatement',
    'ForOfStatement',
]);
function isLoop(node) {
    return LOOP_TYPES.has(node.type);
}
function isSwitch(node) {
    return node.type === 'SwitchStatement';
}
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            removeLabel: 'Refactor the code to remove this label and the need for it.',
        },
    }),
    create(context) {
        // Stack of currently active LabeledStatement nodes (innermost last).
        const labelStack = [];
        // Map from LabeledStatement node to array of booleans.
        // Each boolean is true if the break/continue is inside a nested loop or switch,
        // meaning it legitimately needs the label to exit the enclosing construct.
        const labelRefs = new Map();
        function onBreakOrContinue(node) {
            if (!node.label) {
                return;
            }
            const labelName = node.label.name;
            // Find the latest matching label on the stack.
            let labeledStmt;
            for (let i = labelStack.length - 1; i >= 0; i--) {
                if (labelStack[i].label.name === labelName) {
                    labeledStmt = labelStack[i];
                    break;
                }
            }
            if (!labeledStmt) {
                return;
            }
            const ancestors = context.sourceCode.getAncestors(node);
            const labelIdx = ancestors.indexOf(labeledStmt);
            // ancestors[labelIdx+1] is the labeled body.
            // True if the break/continue is inside a nested loop or switch:
            // - nested loop: break/continue must target the label to exit multiple levels
            // - nested switch: plain 'break' only exits the switch, so 'break label' is the
            //   only way to exit the enclosing loop from within the switch
            const isNested = ancestors.slice(labelIdx + 2).some(n => isLoop(n) || isSwitch(n));
            const refs = labelRefs.get(labeledStmt);
            if (refs) {
                refs.push(isNested);
            }
            else {
                labelRefs.set(labeledStmt, [isNested]);
            }
        }
        return {
            LabeledStatement(node) {
                labelStack.push(node);
            },
            BreakStatement: onBreakOrContinue,
            ContinueStatement: onBreakOrContinue,
            'LabeledStatement:exit'(node) {
                labelStack.pop();
                const refs = labelRefs.get(node);
                labelRefs.delete(node);
                // Non-loop labeled body: always report (labels on blocks, if-statements, etc.)
                if (!isLoop(node.body)) {
                    context.report({
                        messageId: 'removeLabel',
                        node: node.label,
                    });
                    return;
                }
                // No references: label on loop is unused → report
                if (!refs || refs.length === 0) {
                    context.report({
                        messageId: 'removeLabel',
                        node: node.label,
                    });
                    return;
                }
                // Report if any reference is not from within a nested loop or switch.
                // Suppress if all references legitimately need the label (nested loop or switch exits).
                if (refs.some(r => !r)) {
                    context.report({
                        messageId: 'removeLabel',
                        node: node.label,
                    });
                }
            },
        };
    },
};
