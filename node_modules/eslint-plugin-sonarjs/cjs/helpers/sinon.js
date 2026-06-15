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
    return ((0, module_js_1.getRequireCalls)(context).some(r => r.arguments[0].type === 'Literal' && r.arguments[0].value === 'sinon') || (0, module_js_1.getImportDeclarations)(context).some(i => i.source.value === 'sinon'));
}
function isAssertion(context, node) {
    return isAssertUsage(context, node);
}
function isTSAssertion(services, node) {
    if (node.kind !== typescript_1.default.SyntaxKind.CallExpression) {
        return false;
    }
    const fqn = (0, module_ts_js_1.getFullyQualifiedNameTS)(services, node);
    return isFQNAssertion(fqn);
}
function isAssertUsage(context, node) {
    // assert.<expr>(), sinon.assert.<expr>()
    const fqn = extractFQNforCallExpression(context, node);
    return isFQNAssertion(fqn);
}
function isFQNAssertion(fqn) {
    if (!fqn) {
        return false;
    }
    const names = fqn.split('.');
    return names.length === 3 && names[0] === 'sinon' && names[1] === 'assert';
}
function extractFQNforCallExpression(context, node) {
    if (node.type !== 'CallExpression') {
        return undefined;
    }
    return (0, module_js_1.getFullyQualifiedName)(context, node);
}
