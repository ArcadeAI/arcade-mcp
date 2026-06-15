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
// https://sonarsource.github.io/rspec/#/rspec/S8441/javascript
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
const express_js_1 = require("../helpers/express.js");
const ast_js_1 = require("../helpers/ast.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const module_js_1 = require("../helpers/module.js");
const location_js_1 = require("../helpers/location.js");
// If a rule has a schema, use this to extract it.
// import { FromSchema } from 'json-schema-to-ts';
const meta = __importStar(require("./generated-meta.js"));
const messages = {
    sessionSecondaryLocation: 'Session middleware declared here.',
    moveStaticBeforeSession: 'Move this static middleware before the session middleware.',
};
// Extend this list to support additional session-cookie middlewares.
const SESSION_MIDDLEWARES = ['express-session', 'cookie-session'];
const STATIC_MIDDLEWARES = ['express.static'];
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, { messages }),
    create(context) {
        let app = null;
        let lastSessionMiddleware = null;
        const scopeStack = [];
        function isMiddleware(context, node, names) {
            if (node.type !== 'CallExpression') {
                return false;
            }
            const fqn = (0, module_js_1.getFullyQualifiedName)(context, node);
            return fqn !== null && names.includes(fqn);
        }
        return {
            Program() {
                app = null;
                lastSessionMiddleware = null;
                scopeStack.length = 0;
            },
            ':function'(node) {
                scopeStack.push({ app, lastSessionMiddleware });
                const injectedApp = (0, express_js_1.attemptFindAppInjection)(node, context, node);
                if (injectedApp) {
                    app = injectedApp;
                    lastSessionMiddleware = null;
                }
            },
            ':function:exit'() {
                const previous = scopeStack.pop();
                if (previous) {
                    app = previous.app;
                    lastSessionMiddleware = previous.lastSessionMiddleware;
                }
            },
            VariableDeclarator(node) {
                const varDecl = node;
                const instantiatedApp = (0, express_js_1.attemptFindAppInstantiation)(varDecl, context);
                if (instantiatedApp) {
                    app = instantiatedApp;
                    lastSessionMiddleware = null;
                }
            },
            CallExpression(node) {
                if (!app) {
                    return;
                }
                const callExpr = node;
                if (!(0, ast_js_1.isMethodInvocation)(callExpr, app.name, 'use', 1)) {
                    return;
                }
                const flattenedArgs = (0, ast_js_1.flattenArgs)(context, callExpr.arguments);
                for (const middlewareNode of flattenedArgs) {
                    if (isMiddleware(context, middlewareNode, SESSION_MIDDLEWARES)) {
                        lastSessionMiddleware = callExpr;
                        continue;
                    }
                    if (lastSessionMiddleware && isMiddleware(context, middlewareNode, STATIC_MIDDLEWARES)) {
                        (0, location_js_1.report)(context, {
                            node: callExpr,
                            messageId: 'moveStaticBeforeSession',
                            message: messages.moveStaticBeforeSession,
                        }, [(0, location_js_1.toSecondaryLocation)(lastSessionMiddleware, messages.sessionSecondaryLocation)]);
                    }
                }
            },
        };
    },
};
