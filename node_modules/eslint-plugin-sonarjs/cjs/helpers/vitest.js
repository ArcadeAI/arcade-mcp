"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.isImported = isImported;
exports.isAssertion = isAssertion;
exports.isTSAssertion = isTSAssertion;
const module_js_1 = require("./module.js");
const module_ts_js_1 = require("./module-ts.js");
const typescript_1 = __importDefault(require("typescript"));
function isImported(context) {
    return ((0, module_js_1.getRequireCalls)(context).some(r => r.arguments[0].type === 'Literal' && r.arguments[0].value === 'vitest') || (0, module_js_1.getImportDeclarations)(context).some(i => i.source.value === 'vitest'));
}
function isAssertion(context, node) {
    const fullyQualifiedName = extractFQNforCallExpression(context, node);
    return isFQNAssertion(fullyQualifiedName);
}
function isTSAssertion(services, node) {
    if (node.kind !== typescript_1.default.SyntaxKind.CallExpression) {
        return false;
    }
    const fqn = (0, module_ts_js_1.getFullyQualifiedNameTS)(services, node);
    return isFQNAssertion(fqn);
}
function isFQNAssertion(fqn) {
    if (!fqn) {
        return false;
    }
    const validAssertionCalls = ['vitest.expect', 'vitest.expectTypeOf', 'vitest.assertType'];
    return validAssertionCalls.some(callPrefix => fqn.startsWith(callPrefix));
}
function extractFQNforCallExpression(context, node) {
    if (node.type !== 'CallExpression') {
        return undefined;
    }
    return (0, module_js_1.getFullyQualifiedName)(context, node);
}
