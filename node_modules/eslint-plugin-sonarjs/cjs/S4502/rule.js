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
// https://sonarsource.github.io/rspec/#/rspec/S4502/javascript
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
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
const CSURF_MODULE = 'csurf';
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        let globalCsrfProtection = false;
        let importedCsrfMiddleware = false;
        function checkIgnoredMethods(node) {
            if (node.value.type === 'ArrayExpression') {
                const arrayExpr = node.value;
                const unsafeMethods = arrayExpr.elements
                    .filter(ast_js_1.isLiteral)
                    .filter(e => typeof e.value === 'string' && !SAFE_METHODS.has(e.value));
                if (unsafeMethods.length > 0) {
                    const [first, ...rest] = unsafeMethods;
                    (0, location_js_1.report)(context, {
                        message: 'Make sure disabling CSRF protection is safe here.',
                        node: first,
                    }, rest.map(node => (0, location_js_1.toSecondaryLocation)(node)));
                }
            }
        }
        function isCsurfMiddleware(node) {
            return node && (0, module_js_1.getFullyQualifiedName)(context, node) === CSURF_MODULE;
        }
        function checkCallExpression(callExpression) {
            const { callee } = callExpression;
            // require('csurf')
            if ((0, ast_js_1.isRequireModule)(callExpression, CSURF_MODULE)) {
                importedCsrfMiddleware = true;
            }
            // csurf(...)
            if ((0, module_js_1.getFullyQualifiedName)(context, callee) === CSURF_MODULE) {
                const [args] = callExpression.arguments;
                const ignoredMethods = (0, ast_js_1.getProperty)(args, 'ignoreMethods', context);
                if (ignoredMethods) {
                    checkIgnoredMethods(ignoredMethods);
                }
            }
            // app.use(csurf(...))
            if (callee.type === 'MemberExpression') {
                if ((0, ast_js_1.isIdentifier)(callee.property, 'use') &&
                    (0, ast_js_1.flattenArgs)(context, callExpression.arguments).some(isCsurfMiddleware)) {
                    globalCsrfProtection = true;
                }
                if ((0, ast_js_1.isIdentifier)(callee.property, 'post', 'put', 'delete', 'patch') &&
                    !globalCsrfProtection &&
                    importedCsrfMiddleware &&
                    !callExpression.arguments.some(arg => isCsurfMiddleware(arg))) {
                    (0, location_js_1.report)(context, {
                        message: 'Make sure not using CSRF protection is safe here.',
                        node: callee,
                    });
                }
            }
        }
        return {
            Program() {
                globalCsrfProtection = false;
            },
            CallExpression(node) {
                checkCallExpression(node);
            },
            ImportDeclaration(node) {
                if (node.source.value === CSURF_MODULE) {
                    importedCsrfMiddleware = true;
                }
            },
        };
    },
};
