"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.isImported = isImported;
exports.isTSAssertion = isTSAssertion;
exports.isAssertion = isAssertion;
const module_js_1 = require("./module.js");
const module_ts_js_1 = require("./module-ts.js");
const ast_js_1 = require("./ast.js");
const typescript_1 = __importDefault(require("typescript"));
function isImported(context) {
    return ((0, module_js_1.getRequireCalls)(context).some(r => r.arguments[0].type === 'Literal' && r.arguments[0].value === 'chai') || (0, module_js_1.getImportDeclarations)(context).some(i => i.source.value === 'chai'));
}
function isTSAssertion(services, node) {
    if (node.kind !== typescript_1.default.SyntaxKind.CallExpression) {
        return false;
    }
    const fqn = (0, module_ts_js_1.getFullyQualifiedNameTS)(services, node);
    if (!fqn) {
        return false;
    }
    return fqn.startsWith('chai.assert') || fqn.startsWith('chai.expect') || fqn.includes('should');
}
function isAssertion(context, node) {
    return isAssertUsage(context, node) || isExpectUsage(context, node) || isShouldUsage(node);
}
function isAssertUsage(context, node) {
    // assert(), assert.<expr>(), chai.assert(), chai.assert.<expr>()
    const fqn = extractFQNforCallExpression(context, node);
    if (!fqn) {
        return false;
    }
    const names = fqn.split('.');
    return names[0] === 'chai' && names[1] === 'assert';
}
function isExpectUsage(context, node) {
    // expect(), chai.expect()
    return extractFQNforCallExpression(context, node) === 'chai.expect';
}
function isShouldUsage(node) {
    // <expr>.should.<expr>
    return node.type === 'MemberExpression' && (0, ast_js_1.isIdentifier)(node.property, 'should');
}
function extractFQNforCallExpression(context, node) {
    if (node.type !== 'CallExpression') {
        return undefined;
    }
    return (0, module_js_1.getFullyQualifiedName)(context, node);
}
