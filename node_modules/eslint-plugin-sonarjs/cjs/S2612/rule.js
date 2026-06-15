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
// https://sonarsource.github.io/rspec/#/rspec/S2612/javascript
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
const module_js_1 = require("../helpers/module.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
const chmodLikeFunction = ['chmod', 'chmodSync', 'fchmod', 'fchmodSync', 'lchmod', 'lchmodSync'];
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            safePermission: 'Make sure this permission is safe.',
        },
    }),
    create(context) {
        // fs.constants have these value only when running on linux, we need to hardcode them to be able to test on win
        const FS_CONST = {
            S_IRWXU: 0o700,
            S_IRUSR: 0o400,
            S_IWUSR: 0o200,
            S_IXUSR: 0o100,
            S_IRWXG: 0o70,
            S_IRGRP: 0o40,
            S_IWGRP: 0o20,
            S_IXGRP: 0o10,
            S_IRWXO: 0o7,
            S_IROTH: 0o4,
            S_IWOTH: 0o2,
            S_IXOTH: 0o1,
        };
        function modeFromMemberExpression(modeExpr) {
            const { object, property } = modeExpr;
            if ((0, ast_js_1.isMemberExpression)(object, 'fs', 'constants') && property.type === 'Identifier') {
                return FS_CONST[property.name];
            }
            return null;
        }
        function modeFromExpression(expr, visited) {
            if (!expr) {
                return null;
            }
            if (expr.type === 'MemberExpression') {
                return modeFromMemberExpression(expr);
            }
            else if (expr.type === 'Literal') {
                return modeFromLiteral(expr);
            }
            else if (expr.type === 'Identifier') {
                const usage = (0, ast_js_1.getUniqueWriteUsage)(context, expr.name, expr);
                if (usage && !visited.has(usage)) {
                    visited.add(usage);
                    return modeFromExpression(usage, visited);
                }
            }
            else if (expr.type === 'BinaryExpression') {
                const { left, operator, right } = expr;
                if (operator === '|') {
                    const leftValue = modeFromExpression(left, visited);
                    const rightValue = modeFromExpression(right, visited);
                    if (leftValue && rightValue) {
                        return leftValue | rightValue;
                    }
                }
            }
            return null;
        }
        function checkModeArgument(node, moduloTest) {
            const visited = new Set();
            const mode = modeFromExpression(node, visited);
            if (mode !== null && !Number.isNaN(mode) && mode % 8 !== moduloTest) {
                context.report({
                    node,
                    messageId: 'safePermission',
                });
            }
        }
        return {
            CallExpression: (node) => {
                const callExpression = node;
                if (isChmodLikeFunction(callExpression)) {
                    checkModeArgument(callExpression.arguments[0], 0);
                    checkModeArgument(callExpression.arguments[1], 0);
                }
                else if ((0, module_js_1.getFullyQualifiedName)(context, callExpression) === 'process.umask') {
                    checkModeArgument(callExpression.arguments[0], 7);
                }
            },
        };
    },
};
function isChmodLikeFunction(node) {
    const { callee } = node;
    if (callee.type !== 'MemberExpression') {
        return false;
    }
    // to support fs promises we are only checking the name of the function
    return (0, ast_js_1.isIdentifier)(callee.property, ...chmodLikeFunction);
}
function modeFromLiteral(modeExpr) {
    const modeValue = modeExpr.value;
    let mode = null;
    if (typeof modeValue === 'string') {
        mode = Number.parseInt(modeValue, 8);
    }
    else if (typeof modeValue === 'number') {
        const raw = modeExpr.raw;
        // ts parser interprets number starting with 0 as decimal, we need to parse it as octal value
        if (raw?.startsWith('0') && !raw.startsWith('0o')) {
            mode = Number.parseInt(raw, 8);
        }
        else {
            mode = modeValue;
        }
    }
    return mode;
}
