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
// https://sonarsource.github.io/rspec/#/rspec/S5689/javascript
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
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const module_js_1 = require("../helpers/module.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
const HELMET = 'helmet';
const HIDE_POWERED_BY = 'hide-powered-by';
const HEADER_X_POWERED_BY = 'X-Powered-By'.toLowerCase();
const PROTECTING_MIDDLEWARES = [HELMET, HIDE_POWERED_BY];
/** Expected number of arguments in `app.set`. */
const APP_SET_NUM_ARGS = 2;
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            headerSet: 'Make sure disclosing the fingerprinting of this web technology is safe here.',
            headerDefault: 'This framework implicitly discloses version information by default. Make sure it is safe here.',
        },
    }),
    create(context) {
        let appInstantiation = null;
        let isSafe = false;
        let isExplicitlyUnsafe = false;
        return {
            Program() {
                appInstantiation = null;
                isSafe = false;
                isExplicitlyUnsafe = true;
            },
            CallExpression: (node) => {
                if (!isSafe && appInstantiation) {
                    const callExpr = node;
                    isSafe =
                        (0, express_js_1.isUsingMiddleware)(context, callExpr, appInstantiation, isProtecting(context)) ||
                            isDisabledXPoweredBy(callExpr, appInstantiation) ||
                            isSetFalseXPoweredBy(callExpr, appInstantiation) ||
                            isAppEscaping(callExpr, appInstantiation);
                    isExplicitlyUnsafe = isSetTrueXPoweredBy(callExpr, appInstantiation);
                }
            },
            VariableDeclarator: (node) => {
                if (!isSafe && !appInstantiation) {
                    const varDecl = node;
                    const app = (0, express_js_1.attemptFindAppInstantiation)(varDecl, context);
                    if (app) {
                        appInstantiation = app;
                    }
                }
            },
            ReturnStatement: (node) => {
                if (!isSafe && appInstantiation) {
                    const ret = node;
                    isSafe = isAppEscapingThroughReturn(ret, appInstantiation);
                }
            },
            'Program:exit'() {
                if (!isSafe && appInstantiation) {
                    let messageId = 'headerDefault';
                    if (isExplicitlyUnsafe) {
                        messageId = 'headerSet';
                    }
                    context.report({
                        node: appInstantiation,
                        messageId,
                    });
                }
            },
        };
    },
};
/**
 * Checks whether node looks like `helmet.hidePoweredBy()`.
 */
function isHidePoweredByFromHelmet(context, n) {
    if (n.type === 'CallExpression') {
        return (0, module_js_1.getFullyQualifiedName)(context, n) === `${HELMET}.hidePoweredBy`;
    }
    return false;
}
function isProtecting(context) {
    return (n) => (0, express_js_1.isMiddlewareInstance)(context, PROTECTING_MIDDLEWARES, n) ||
        isHidePoweredByFromHelmet(context, n);
}
function isDisabledXPoweredBy(callExpression, app) {
    if ((0, ast_js_1.isMethodInvocation)(callExpression, app.name, 'disable', 1)) {
        const arg0 = callExpression.arguments[0];
        return arg0.type === 'Literal' && String(arg0.value).toLowerCase() === HEADER_X_POWERED_BY;
    }
    return false;
}
function isSetFalseXPoweredBy(callExpression, app) {
    return getSetTrueXPoweredByValue(callExpression, app) === false;
}
function isSetTrueXPoweredBy(callExpression, app) {
    return getSetTrueXPoweredByValue(callExpression, app) === true;
}
function getSetTrueXPoweredByValue(callExpression, app) {
    if ((0, ast_js_1.isMethodInvocation)(callExpression, app.name, 'set', APP_SET_NUM_ARGS)) {
        const [headerName, onOff] = callExpression.arguments;
        if (headerName.type === 'Literal' &&
            String(headerName.value).toLowerCase() === HEADER_X_POWERED_BY &&
            onOff.type === 'Literal') {
            return onOff.value;
        }
    }
    return undefined;
}
function isAppEscaping(callExpr, app) {
    return Boolean(callExpr.arguments.some(arg => arg.type === 'Identifier' && arg.name === app.name));
}
function isAppEscapingThroughReturn(ret, app) {
    const arg = ret.argument;
    return Boolean(arg?.type === 'Identifier' && arg.name === app.name);
}
