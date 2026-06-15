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
// https://sonarsource.github.io/rspec/#/rspec/S2819/javascript
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
const type_js_1 = require("../helpers/type.js");
const ast_js_1 = require("../helpers/ast.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const meta = __importStar(require("./generated-meta.js"));
const POST_MESSAGE = 'postMessage';
const ADD_EVENT_LISTENER = 'addEventListener';
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            specifyTarget: `Specify a target origin for this message.`,
            verifyOrigin: `Verify the origin of the received message.`,
        },
    }),
    create(context) {
        const services = context.sourceCode.parserServices;
        if (!(0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {};
        }
        return {
            [`CallExpression:matches([callee.name="${POST_MESSAGE}"], [callee.property.name="${POST_MESSAGE}"])`]: (node) => {
                checkPostMessageCall(node, context);
            },
            [`CallExpression[callee.property.name="${ADD_EVENT_LISTENER}"]`]: (node) => {
                checkAddEventListenerCall(node, context);
            },
        };
    },
};
function isWindowObject(node, context) {
    const type = (0, type_js_1.getTypeAsString)(node, context.sourceCode.parserServices);
    const hasWindowName = WindowNameVisitor.containsWindowName(node, context);
    return type.match(/window/i) || type.match(/globalThis/i) || hasWindowName;
}
function checkPostMessageCall(callExpr, context) {
    const { callee } = callExpr;
    // Window.postMessage() can take 2 or 3 arguments
    if (![2, 3].includes(callExpr.arguments.length) ||
        (0, ast_js_1.getValueOfExpression)(context, callExpr.arguments[1], 'Literal')?.value !== '*') {
        return;
    }
    if (callee.type === 'Identifier') {
        context.report({
            node: callee,
            messageId: 'specifyTarget',
        });
    }
    if (callee.type !== 'MemberExpression') {
        return;
    }
    if (isWindowObject(callee.object, context)) {
        context.report({
            node: callee,
            messageId: 'specifyTarget',
        });
    }
}
function checkAddEventListenerCall(callExpr, context) {
    const { callee, arguments: args } = callExpr;
    if (!isWindowObject(callee, context) ||
        args.length < 2 ||
        !isMessageTypeEvent(args[0], context)) {
        return;
    }
    let listener = (0, ast_js_1.resolveFunction)(context, args[1]);
    if (listener?.body.type === 'CallExpression') {
        listener = (0, ast_js_1.resolveFunction)(context, listener.body);
    }
    if (!listener || listener.params.length === 0) {
        return;
    }
    const event = listener.params[0];
    if (event.type !== 'Identifier') {
        return;
    }
    if (!hasVerifiedOrigin(context, listener, event)) {
        context.report({
            node: callee,
            messageId: 'verifyOrigin',
        });
    }
}
/**
 * Checks if event.origin or event.originalEvent.origin is verified
 */
function hasVerifiedOrigin(context, listener, event) {
    const scope = context.sourceCode.scopeManager.acquire(listener);
    const eventVariable = scope?.variables.find(v => v.name === event.name);
    if (eventVariable) {
        const eventIdentifiers = eventVariable.references.map(e => e.identifier);
        for (const reference of eventVariable.references) {
            const eventRef = reference.identifier;
            if (isEventOriginCompared(eventRef) || isEventOriginalEventCompared(eventRef)) {
                return true;
            }
            // event OR-ed with event.originalEvent
            const unionEvent = findUnionEvent(eventRef, eventIdentifiers);
            if (unionEvent !== null && isReferenceCompared(scope, unionEvent)) {
                return true;
            }
            // event.origin OR-ed with event.originalEvent.origin
            const unionOrigin = findUnionOrigin(eventRef, eventIdentifiers);
            if (unionOrigin !== null &&
                isEventOriginReferenceCompared(scope, unionOrigin)) {
                return true;
            }
        }
    }
    return false;
    /**
     * Looks for unionEvent = event | event.originalEvent
     */
    function findUnionEvent(event, eventIdentifiers) {
        const logicalExpr = event.parent;
        if (logicalExpr?.type !== 'LogicalExpression') {
            return null;
        }
        if ((logicalExpr.left === event &&
            isEventOriginalEvent(logicalExpr.right, eventIdentifiers)) ||
            (logicalExpr.right === event &&
                isEventOriginalEvent(logicalExpr.left, eventIdentifiers))) {
            return extractVariableDeclaratorIfExists(logicalExpr);
        }
        return null;
    }
    /**
     * looks for unionOrigin = event.origin | event.originalEvent.origin
     */
    function findUnionOrigin(eventRef, eventIdentifiers) {
        const memberExpr = eventRef.parent;
        // looks for event.origin in a LogicalExpr
        if (!(memberExpr?.type === 'MemberExpression' && memberExpr.parent?.type === 'LogicalExpression')) {
            return null;
        }
        const logicalExpr = memberExpr.parent;
        if (!(logicalExpr.left === memberExpr &&
            isEventOriginalEventOrigin(logicalExpr.right, eventIdentifiers)) &&
            !(logicalExpr.right === memberExpr &&
                isEventOriginalEventOrigin(logicalExpr.left, eventIdentifiers))) {
            return null;
        }
        return extractVariableDeclaratorIfExists(logicalExpr);
        /**
         * checks if memberExpr is event.originalEvent.origin
         */
        function isEventOriginalEventOrigin(memberExpr, eventIdentifiers) {
            const subMemberExpr = memberExpr.object;
            if (subMemberExpr?.type !== 'MemberExpression') {
                return false;
            }
            const isOrigin = memberExpr.property.type === 'Identifier' && memberExpr.property.name === 'origin';
            return isEventOriginalEvent(subMemberExpr, eventIdentifiers) && isOrigin;
        }
    }
}
/**
 * Looks for an occurrence of the provided node in an IfStatement
 */
function isReferenceCompared(scope, identifier) {
    function getGrandParent(node) {
        return node?.parent?.parent;
    }
    return checkReference(scope, identifier, getGrandParent);
}
/**
 * checks if a reference of identifier is
 * node.identifier
 */
function isEventOriginReferenceCompared(scope, identifier) {
    function getParent(node) {
        return node?.parent;
    }
    return checkReference(scope, identifier, getParent);
}
/**
 *
 */
function checkReference(scope, identifier, callback) {
    const identifierVariable = scope?.variables.find(v => v.name === identifier.name);
    if (!identifierVariable) {
        return false;
    }
    for (const reference of identifierVariable.references) {
        const binaryExpressionCandidate = callback(reference.identifier);
        if (isInIfStatement(binaryExpressionCandidate)) {
            return true;
        }
    }
    return false;
}
/**
 * checks if memberExpr is event.originalEvent
 */
function isEventOriginalEvent(memberExpr, eventIdentifiers) {
    const isEvent = memberExpr.object.type === 'Identifier' &&
        eventIdentifiers.includes(memberExpr.object);
    const isOriginalEvent = memberExpr.property.type === 'Identifier' && memberExpr.property.name === 'originalEvent';
    return isEvent && isOriginalEvent;
}
/**
 * Extracts the identifier to which the 'node' expression is assigned to
 */
function extractVariableDeclaratorIfExists(node) {
    if (node.parent?.type !== 'VariableDeclarator') {
        return null;
    }
    return node.parent.id;
}
/**
 * Looks for an IfStatement with event.origin
 */
function isEventOriginCompared(event) {
    const memberExpr = findEventOrigin(event);
    return isInIfStatement(memberExpr);
}
/**
 * Looks for an IfStatement with event.originalEvent.origin
 */
function isEventOriginalEventCompared(event) {
    const eventOriginalEvent = findEventOriginalEvent(event);
    if (!eventOriginalEvent?.parent) {
        return false;
    }
    if (!isPropertyOrigin(eventOriginalEvent.parent)) {
        return false;
    }
    return isInIfStatement(eventOriginalEvent);
}
/**
 * Returns event.origin MemberExpression, if exists
 */
function findEventOrigin(event) {
    const parent = event.parent;
    if (parent?.type !== 'MemberExpression') {
        return null;
    }
    if (isPropertyOrigin(parent)) {
        return parent;
    }
    else {
        return null;
    }
}
/**
 * Checks if node has a property 'origin'
 */
function isPropertyOrigin(node) {
    return (0, ast_js_1.isIdentifier)(node.property, 'origin');
}
/**
 * Returns event.originalEvent MemberExpression, if exists
 */
function findEventOriginalEvent(event) {
    const memberExpr = event.parent;
    if (memberExpr?.type !== 'MemberExpression') {
        return null;
    }
    const { object: eventCandidate, property: originalEventIdentifierCandidate } = memberExpr;
    if (eventCandidate === event &&
        (0, ast_js_1.isIdentifier)(originalEventIdentifierCandidate, 'originalEvent')) {
        return memberExpr;
    }
    return null;
}
/**
 * Checks if the current node is nested in an IfStatement
 */
function isInIfStatement(node) {
    // this checks for 'undefined' and 'null', because node.parent can be 'null'
    if (node == null) {
        return false;
    }
    return (0, ancestor_js_1.findFirstMatchingLocalAncestor)(node, ast_js_1.isIfStatement) != null;
}
function isMessageTypeEvent(eventNode, context) {
    const eventValue = (0, ast_js_1.getValueOfExpression)(context, eventNode, 'Literal');
    return typeof eventValue?.value === 'string' && eventValue.value.toLowerCase() === 'message';
}
class WindowNameVisitor {
    constructor() {
        this.hasWindowName = false;
    }
    static containsWindowName(node, context) {
        const visitor = new WindowNameVisitor();
        visitor.visit(node, context);
        return visitor.hasWindowName;
    }
    visit(root, context) {
        const visitNode = (node) => {
            if (node.type === 'Identifier' && /window/i.test(node.name)) {
                this.hasWindowName = true;
            }
            for (const childNode of (0, ancestor_js_1.childrenOf)(node, context.sourceCode.visitorKeys)) {
                visitNode(childNode);
            }
        };
        visitNode(root);
    }
}
