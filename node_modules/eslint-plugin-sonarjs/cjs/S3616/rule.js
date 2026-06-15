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
// https://sonarsource.github.io/rspec/#/rspec/S3616/javascript
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
const ast_js_1 = require("../helpers/ast.js");
const collection_js_1 = require("../helpers/collection.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            specifyCase: `Explicitly specify {{nesting}} separate cases that fall through; currently this case clause only works for "{{expression}}".`,
        },
    }),
    create(context) {
        function reportIssue(node, clause, nestingLvl) {
            context.report({
                messageId: 'specifyCase',
                data: {
                    nesting: nestingLvl.toString(),
                    expression: String(getTextFromNode(clause)),
                },
                node,
            });
        }
        function getTextFromNode(node) {
            if (node.type === 'Literal') {
                return node.value;
            }
            else {
                return context.sourceCode.getText(node);
            }
        }
        return {
            'SwitchCase > SequenceExpression'(node) {
                const expressions = node.expressions;
                reportIssue(node, (0, collection_js_1.last)(expressions), expressions.length);
            },
            'SwitchCase > LogicalExpression'(node) {
                if (!isSwitchTrue(getEnclosingSwitchStatement(context, node))) {
                    const firstElemAndNesting = getFirstElementAndNestingLevel(node, 0);
                    if (firstElemAndNesting) {
                        reportIssue(node, firstElemAndNesting[0], firstElemAndNesting[1] + 1);
                    }
                }
            },
        };
    },
};
function getEnclosingSwitchStatement(context, node) {
    const ancestors = context.sourceCode.getAncestors(node);
    for (let i = ancestors.length - 1; i >= 0; i--) {
        if (ancestors[i].type === 'SwitchStatement') {
            return ancestors[i];
        }
    }
    throw new Error('A switch case should have an enclosing switch statement');
}
function isSwitchTrue(node) {
    return (0, ast_js_1.isLiteral)(node.discriminant) && node.discriminant.value === true;
}
function getFirstElementAndNestingLevel(logicalExpression, currentLvl) {
    if (logicalExpression.operator === '||') {
        if (logicalExpression.left.type === 'LogicalExpression') {
            return getFirstElementAndNestingLevel(logicalExpression.left, currentLvl + 1);
        }
        else {
            return [logicalExpression.left, currentLvl + 1];
        }
    }
    return undefined;
}
