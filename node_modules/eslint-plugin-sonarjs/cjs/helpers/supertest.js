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
    return ((0, module_js_1.getRequireCalls)(context).some(r => r.arguments[0].type === 'Literal' && r.arguments[0].value === 'supertest') || (0, module_js_1.getImportDeclarations)(context).some(i => i.source.value === 'supertest'));
}
function isAssertion(context, node) {
    const fqn = extractFQNForCallExpression(context, node);
    return isFQNAssertion(fqn);
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
    const names = fqn.split('.');
    /**
     * supertest assertions look like `[supertest instance](...).[HTTP verb](...).expect(...)`, typically:
     * `supertest(application).get('/foo').expect(200)`
     * hence only the first and third values matter, the second one being an HTTP verb irrelevant for assertion detection
     */
    return names.length >= 3 && names[0] === 'supertest' && names[2] === 'expect';
}
function extractFQNForCallExpression(context, node) {
    if (node.type !== 'CallExpression') {
        return undefined;
    }
    return (0, module_js_1.getFullyQualifiedName)(context, node);
}
