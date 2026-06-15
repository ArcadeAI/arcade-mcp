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
// https://sonarsource.github.io/rspec/#/rspec/S4822/javascript
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
const ancestor_js_1 = require("../helpers/ancestor.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const type_js_1 = require("../helpers/type.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const services = context.sourceCode.parserServices;
        if ((0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {
                TryStatement: (node) => visitTryStatement(node, context, services),
            };
        }
        return {};
    },
};
function visitTryStatement(tryStmt, context, services) {
    if (tryStmt.handler) {
        // without '.catch()'
        const openPromises = [];
        // with '.catch()'
        const capturedPromises = [];
        let hasPotentiallyThrowingCalls = false;
        for (const callLikeExpr of CallLikeExpressionVisitor.getCallExpressions(tryStmt.block, context)) {
            if (callLikeExpr.type === 'AwaitExpression' ||
                !(0, type_js_1.isThenable)(callLikeExpr, services)) {
                hasPotentiallyThrowingCalls = true;
                continue;
            }
            if (isAwaitLike(callLikeExpr) || isThened(callLikeExpr) || isCatch(callLikeExpr)) {
                continue;
            }
            (isCaught(callLikeExpr) ? capturedPromises : openPromises).push(callLikeExpr);
        }
        if (!hasPotentiallyThrowingCalls) {
            checkForWrongCatch(tryStmt, openPromises, context);
            checkForUselessCatch(tryStmt, openPromises, capturedPromises, context);
        }
    }
}
class CallLikeExpressionVisitor {
    constructor() {
        this.callLikeExpressions = [];
    }
    static getCallExpressions(node, context) {
        const visitor = new CallLikeExpressionVisitor();
        visitor.visit(node, context);
        return visitor.callLikeExpressions;
    }
    visit(root, context) {
        const visitNode = (node) => {
            switch (node.type) {
                case 'AwaitExpression':
                case 'CallExpression':
                case 'NewExpression':
                    this.callLikeExpressions.push(node);
                    break;
                case 'FunctionDeclaration':
                case 'FunctionExpression':
                case 'ArrowFunctionExpression':
                    return;
            }
            for (const childNode of (0, ancestor_js_1.childrenOf)(node, context.sourceCode.visitorKeys)) {
                visitNode(childNode);
            }
        };
        visitNode(root);
    }
}
function checkForWrongCatch(tryStmt, openPromises, context) {
    if (openPromises.length > 0) {
        const ending = openPromises.length > 1 ? 's' : '';
        const message = `Consider using 'await' for the promise${ending} inside this 'try' or replace it with 'Promise.prototype.catch(...)' usage${ending}.`;
        const token = context.sourceCode.getFirstToken(tryStmt);
        (0, location_js_1.report)(context, {
            message,
            loc: token.loc,
        }, openPromises.map(node => (0, location_js_1.toSecondaryLocation)(node, 'Promise')));
    }
}
function checkForUselessCatch(tryStmt, openPromises, capturedPromises, context) {
    if (openPromises.length === 0 && capturedPromises.length > 0) {
        const ending = capturedPromises.length > 1 ? 's' : '';
        const message = `Consider removing this 'try' statement as promise${ending} rejection is already captured by '.catch()' method.`;
        const token = context.sourceCode.getFirstToken(tryStmt);
        (0, location_js_1.report)(context, {
            message,
            loc: token.loc,
        }, capturedPromises.map(node => (0, location_js_1.toSecondaryLocation)(node, 'Caught promise')));
    }
}
function isAwaitLike(callExpr) {
    return (callExpr.parent &&
        (callExpr.parent.type === 'AwaitExpression' || callExpr.parent.type === 'YieldExpression'));
}
function isThened(callExpr) {
    return (callExpr.parent?.type === 'MemberExpression' &&
        callExpr.parent.property.type === 'Identifier' &&
        callExpr.parent.property.name === 'then');
}
function isCaught(callExpr) {
    return (callExpr.parent?.type === 'MemberExpression' &&
        callExpr.parent.property.type === 'Identifier' &&
        callExpr.parent.property.name === 'catch');
}
function isCatch(callExpr) {
    return (callExpr.type === 'CallExpression' &&
        callExpr.callee.type === 'MemberExpression' &&
        callExpr.callee.property.type === 'Identifier' &&
        callExpr.callee.property.name === 'catch');
}
