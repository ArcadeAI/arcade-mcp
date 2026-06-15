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
// https://sonarsource.github.io/rspec/#/rspec/S1764
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
const location_js_1 = require("../helpers/location.js");
const equivalence_js_1 = require("../helpers/equivalence.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
const sonar_runtime_js_1 = require("../helpers/sonar-runtime.js");
const EQUALITY_OPERATOR_TOKEN_KINDS = new Set(['==', '===', '!=', '!==']);
// consider only binary expressions with these operators
const RELEVANT_OPERATOR_TOKEN_KINDS = new Set([
    '&&',
    '||',
    '/',
    '-',
    '<<',
    '>>',
    '<',
    '<=',
    '>',
    '>=',
]);
function hasRelevantOperator(node) {
    return (RELEVANT_OPERATOR_TOKEN_KINDS.has(node.operator) ||
        (EQUALITY_OPERATOR_TOKEN_KINDS.has(node.operator) && !hasIdentifierOperands(node)));
}
function hasIdentifierOperands(node) {
    return (0, ast_js_1.isIdentifier)(node.left) && (0, ast_js_1.isIdentifier)(node.right);
}
function isOneOntoOneShifting(node) {
    return (node.operator === '<<' &&
        (0, ast_js_1.isLiteral)(node.left) &&
        (node.left.value === 1 || node.left.value === 1n));
}
const message = 'Correct one of the identical sub-expressions on both sides of operator "{{operator}}"';
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            correctIdenticalSubExpressions: message,
        },
    }),
    create(context) {
        return {
            LogicalExpression(node) {
                check(node);
            },
            BinaryExpression(node) {
                check(node);
            },
        };
        function check(expr) {
            if (hasRelevantOperator(expr) &&
                !isOneOntoOneShifting(expr) &&
                (0, equivalence_js_1.areEquivalent)(expr.left, expr.right, context.sourceCode)) {
                const secondaryLocations = [];
                if (expr.left.loc) {
                    secondaryLocations.push((0, location_js_1.toSecondaryLocation)(expr.left));
                }
                (0, location_js_1.report)(context, {
                    message,
                    messageId: 'correctIdenticalSubExpressions',
                    data: {
                        operator: expr.operator,
                    },
                    node: (0, sonar_runtime_js_1.isSonarRuntime)(context) ? expr.right : expr,
                }, secondaryLocations);
            }
        }
    },
};
