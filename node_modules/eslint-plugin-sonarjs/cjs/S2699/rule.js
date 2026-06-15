"use strict";
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
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.rule = void 0;
const Chai = __importStar(require("../helpers/chai.js"));
const ancestor_js_1 = require("../helpers/ancestor.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const module_js_1 = require("../helpers/module.js");
const module_ts_js_1 = require("../helpers/module-ts.js");
const ast_js_1 = require("../helpers/ast.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const Mocha = __importStar(require("../helpers/mocha.js"));
const Sinon = __importStar(require("../helpers/sinon.js"));
const Vitest = __importStar(require("../helpers/vitest.js"));
const Supertest = __importStar(require("../helpers/supertest.js"));
const meta = __importStar(require("./generated-meta.js"));
const typescript_1 = __importDefault(require("typescript"));
/**
 * We assume that the user is using a single assertion library per file,
 * this is why we are not saving if an assertion has been performed for
 * libX and the imported library was libY.
 */
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        if (!(Chai.isImported(context) ||
            Sinon.isImported(context) ||
            Vitest.isImported(context) ||
            Supertest.isImported(context))) {
            return {};
        }
        const visitedNodes = new Map();
        const visitedTSNodes = new Map();
        return {
            'CallExpression:exit': (node) => {
                const testCase = Mocha.extractTestCase(node);
                if (testCase !== null) {
                    checkAssertions(testCase, context, visitedNodes, visitedTSNodes);
                }
            },
        };
    },
};
/**
 * Checks if a test uses the Mocha done callback as an assertion mechanism.
 * Only valid when done is called with an error argument OR passed to an error-handling position.
 *
 * Valid patterns (considered assertions):
 * - done(arg) - direct call with any argument (e.g., done(new Error(...)))
 * - .catch(done) - done receives rejection error
 * - .then(_, done) - done as second argument receives rejection
 * - .subscribe(_, done) - done as second argument (error position in RxJS)
 * - .subscribe({ error: done }) - done in error property
 *
 * Invalid patterns (NOT assertions):
 * - done() - no argument
 * - .finally(done) - finally handler called without args
 * - finalize(done) - RxJS finalize called without args
 * - .then(done) - done as first/only argument (success handler)
 * - .subscribe(done) - done as first/only argument (next handler)
 */
function hasDoneCallbackAssertion(callback, context) {
    if (callback.params.length === 0) {
        return false;
    }
    const firstParam = callback.params[0];
    if (!(0, ast_js_1.isIdentifier)(firstParam)) {
        return false;
    }
    const doneParamName = firstParam.name;
    const visitorKeys = context.sourceCode.visitorKeys;
    return containsValidDoneAssertion(callback.body, doneParamName, visitorKeys, context);
}
/**
 * Checks if a method call matches valid done assertion patterns.
 * Returns true if the pattern is recognized as a valid assertion mechanism.
 */
function isValidDoneMethodCallPattern(node, doneParamName, context) {
    const methodName = node.callee.property.name;
    // Pattern 2: .catch(done) - done receives rejection error
    if (methodName === 'catch' &&
        node.arguments.length === 1 &&
        (0, ast_js_1.isIdentifier)(node.arguments[0], doneParamName)) {
        return true;
    }
    // Pattern 3: .then(_, done) - done as second argument
    if (methodName === 'then' &&
        node.arguments.length >= 2 &&
        (0, ast_js_1.isIdentifier)(node.arguments[1], doneParamName)) {
        return true;
    }
    // Pattern 4: .subscribe(_, done) - done as second argument (error position)
    if (methodName === 'subscribe' &&
        node.arguments.length >= 2 &&
        (0, ast_js_1.isIdentifier)(node.arguments[1], doneParamName)) {
        return true;
    }
    // Pattern 5: .subscribe({ error: done }) - done in error property
    if (methodName === 'subscribe' &&
        node.arguments.length === 1 &&
        node.arguments[0].type === 'ObjectExpression') {
        const errorProp = (0, ast_js_1.getProperty)(node.arguments[0], 'error', context);
        return errorProp != null && (0, ast_js_1.isIdentifier)(errorProp.value, doneParamName);
    }
    return false;
}
/**
 * Recursively searches for valid done assertion patterns.
 */
function containsValidDoneAssertion(node, doneParamName, visitorKeys, context) {
    if (node.type === 'CallExpression') {
        // Pattern 1: done(arg) - direct call with at least one argument
        if ((0, ast_js_1.isIdentifier)(node.callee, doneParamName) && node.arguments.length > 0) {
            return true;
        }
        // Check method call patterns
        if ((0, ast_js_1.isMethodCall)(node) && isValidDoneMethodCallPattern(node, doneParamName, context)) {
            return true;
        }
    }
    // Recurse through children
    for (const child of (0, ancestor_js_1.childrenOf)(node, visitorKeys)) {
        if (containsValidDoneAssertion(child, doneParamName, visitorKeys, context)) {
            return true;
        }
    }
    return false;
}
function checkAssertions(testCase, context, visitedNodes, visitedTSNodes) {
    const { node, callback } = testCase;
    // Check for Mocha done(error) callback pattern used as assertion mechanism
    if (hasDoneCallbackAssertion(callback, context)) {
        return;
    }
    const visitor = new TestCaseAssertionVisitor(context);
    const parserServices = context.sourceCode.parserServices;
    let hasAssertions = false;
    if ((0, parser_services_js_1.isRequiredParserServices)(parserServices)) {
        const tsNode = parserServices.esTreeNodeToTSNodeMap.get(callback);
        hasAssertions = visitor.visitTSNode(parserServices, tsNode, visitedTSNodes);
    }
    else {
        hasAssertions = visitor.visit(context, callback.body, visitedNodes);
    }
    if (!hasAssertions) {
        context.report({ node, message: 'Add at least one assertion to this test case.' });
    }
}
class TestCaseAssertionVisitor {
    constructor(context) {
        this.context = context;
        this.visitorKeys = context.sourceCode.visitorKeys;
    }
    visitTSNode(services, node, visitedTSNodes) {
        if (visitedTSNodes.has(node)) {
            return visitedTSNodes.get(node);
        }
        visitedTSNodes.set(node, false);
        if (isGlobalTSAssertion(services, node) ||
            Chai.isTSAssertion(services, node) ||
            Sinon.isTSAssertion(services, node) ||
            Supertest.isTSAssertion(services, node) ||
            Vitest.isTSAssertion(services, node)) {
            visitedTSNodes.set(node, true);
            return true;
        }
        let nodeHasAssertions = false;
        if (node.kind === typescript_1.default.SyntaxKind.CallExpression) {
            const callNode = services.program
                .getTypeChecker()
                .getResolvedSignature(node);
            if (callNode?.declaration) {
                nodeHasAssertions ||= this.visitTSNode(services, callNode.declaration, visitedTSNodes);
            }
        }
        node.forEachChild(child => {
            nodeHasAssertions ||= this.visitTSNode(services, child, visitedTSNodes);
        });
        visitedTSNodes.set(node, nodeHasAssertions);
        return nodeHasAssertions;
    }
    visit(context, node, visitedNodes) {
        if (visitedNodes.has(node)) {
            return visitedNodes.get(node);
        }
        visitedNodes.set(node, false);
        if (Chai.isAssertion(context, node) ||
            Sinon.isAssertion(context, node) ||
            Vitest.isAssertion(context, node) ||
            Supertest.isAssertion(context, node) ||
            isGlobalAssertion(context, node)) {
            visitedNodes.set(node, true);
            return true;
        }
        let nodeHasAssertions = false;
        if ((0, ast_js_1.isFunctionCall)(node)) {
            const { callee } = node;
            const functionDef = (0, ast_js_1.resolveFunction)(this.context, callee);
            if (functionDef) {
                nodeHasAssertions ||= this.visit(context, functionDef.body, visitedNodes);
            }
        }
        for (const child of (0, ancestor_js_1.childrenOf)(node, this.visitorKeys)) {
            nodeHasAssertions ||= this.visit(context, child, visitedNodes);
        }
        visitedNodes.set(node, nodeHasAssertions);
        return nodeHasAssertions;
    }
}
function isGlobalTSAssertion(services, node) {
    if (node.kind !== typescript_1.default.SyntaxKind.CallExpression) {
        return false;
    }
    const callExpressionNode = node;
    // check for global expect
    if (isGlobalExpectExpression(callExpressionNode)) {
        return true;
    }
    return isFunctionCallFromNodeAssertTS(services, node);
}
function isGlobalExpectExpression(node) {
    if (node.expression.kind !== typescript_1.default.SyntaxKind.PropertyAccessExpression) {
        return false;
    }
    // Walk up the chain of property accesses to find the innermost call expression
    // This handles: expect(...).toHaveBeenCalled() as well as expect(...).not.toHaveBeenCalled()
    // Also handles: expectObservable(...).toBe(...), expectSubscriptions(...).toBe(...), etc.
    let current = node.expression.expression;
    while (current.kind === typescript_1.default.SyntaxKind.PropertyAccessExpression) {
        current = current.expression;
    }
    if (current.kind !== typescript_1.default.SyntaxKind.CallExpression) {
        return false;
    }
    const innerCallExpression = current;
    return (innerCallExpression.expression.kind === typescript_1.default.SyntaxKind.Identifier &&
        innerCallExpression.expression.text.startsWith('expect'));
}
function isFunctionCallFromNodeAssertTS(services, node) {
    const fqn = (0, module_ts_js_1.getFullyQualifiedNameTS)(services, node);
    return fqn ? fqn?.startsWith('assert') : false;
}
function isGlobalAssertion(context, node) {
    if (node.type !== 'CallExpression') {
        return false;
    }
    // Check for global expect (mirrors isGlobalExpectExpression for TS)
    if (isGlobalExpectExpressionJS(node)) {
        return true;
    }
    return isFunctionCallFromNodeAssert(context, node);
}
/**
 * Checks if the node matches the pattern expectX(...).method() where:
 * - expectX is a function whose name starts with "expect" (e.g., expect, expectObservable, expectSubscriptions, expectTypeOf)
 * - method is a chained property access with a method call (e.g., .toBe(), .toEqual(), .not.toBe())
 *
 * This mirrors the TypeScript isGlobalExpectExpression function logic.
 */
function isGlobalExpectExpressionJS(node) {
    if (node.callee.type !== 'MemberExpression') {
        return false;
    }
    // Walk up the chain of member expressions to find the innermost call expression
    // This handles: expect(...).toBe() as well as expect(...).not.toBe()
    // Also handles: expectObservable(...).toBe(...), expectSubscriptions(...).toBe(...), etc.
    let current = node.callee.object;
    while (current.type === 'MemberExpression') {
        current = current.object;
    }
    if (current.type !== 'CallExpression') {
        return false;
    }
    const innerCall = current;
    return innerCall.callee.type === 'Identifier' && innerCall.callee.name.startsWith('expect');
}
function isFunctionCallFromNodeAssert(context, node) {
    const fullyQualifiedName = (0, module_js_1.getFullyQualifiedName)(context, node);
    return fullyQualifiedName?.split('.')[0] === 'assert';
}
