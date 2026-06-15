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
// https://sonarsource.github.io/rspec/#/rspec/S4507/javascript
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
const ast_js_1 = require("../helpers/ast.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const module_js_1 = require("../helpers/module.js");
const meta = __importStar(require("./generated-meta.js"));
const ERRORHANDLER_MODULE = 'errorhandler';
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            deactivateDebug: 'Make sure this debug feature is deactivated before delivering the code in production.',
        },
    }),
    create(context) {
        return {
            CallExpression(node) {
                const callExpression = node;
                // app.use(...)
                checkErrorHandlerMiddleware(context, callExpression);
            },
        };
    },
};
function checkErrorHandlerMiddleware(context, callExpression) {
    const { callee, arguments: args } = callExpression;
    if ((0, ast_js_1.isMemberWithProperty)(callee, 'use') &&
        args.length > 0 &&
        !isInsideConditional(context, callExpression)) {
        for (const m of (0, ast_js_1.flattenArgs)(context, args)) {
            const middleware = (0, ast_js_1.getUniqueWriteUsageOrNode)(context, m);
            if (middleware.type === 'CallExpression' &&
                (0, module_js_1.getFullyQualifiedName)(context, middleware) === ERRORHANDLER_MODULE) {
                context.report({
                    node: middleware,
                    messageId: 'deactivateDebug',
                });
            }
        }
    }
}
function isInsideConditional(context, node) {
    const ancestors = context.sourceCode.getAncestors(node);
    return ancestors.some(ancestor => ancestor.type === 'IfStatement');
}
