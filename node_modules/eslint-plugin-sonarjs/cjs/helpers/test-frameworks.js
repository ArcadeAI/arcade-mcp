"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.TEST_FRAMEWORK_STRUCTURE_FUNCTIONS = void 0;
exports.isTestFrameworkCall = isTestFrameworkCall;
/**
 * Test framework structural functions whose callbacks define test structure
 * rather than business logic. Covers: Mocha, Jest, Vitest, Jasmine, Node.js test runner.
 */
exports.TEST_FRAMEWORK_STRUCTURE_FUNCTIONS = new Set([
    // Test suites
    'describe',
    'context', // Mocha alias for describe
    'suite', // Mocha TDD interface
    // Test cases
    'it',
    'test',
    'specify', // Mocha alias for it
    // Lifecycle hooks
    'before',
    'after',
    'beforeEach',
    'afterEach',
    'beforeAll', // Jest, Vitest
    'afterAll', // Jest, Vitest
    // Skipped tests (Mocha, Jest, Jasmine)
    'xdescribe',
    'xcontext',
    'xit',
    'xtest',
    // Focused tests (Mocha, Jest, Jasmine)
    'fdescribe',
    'fcontext',
    'fit',
    'ftest',
]);
/**
 * Checks if a CallExpression is a test framework structural function.
 * Handles both direct calls (describe()) and member expressions (describe.only()).
 */
function isTestFrameworkCall(node) {
    if (node.type !== 'CallExpression') {
        return false;
    }
    const { callee } = node;
    // Direct call: describe("test", () => {})
    if (callee.type === 'Identifier') {
        return exports.TEST_FRAMEWORK_STRUCTURE_FUNCTIONS.has(callee.name);
    }
    // Member expression: describe.only("test", () => {}), test.skip("test", () => {}), etc.
    if (callee.type === 'MemberExpression' && callee.object.type === 'Identifier') {
        return exports.TEST_FRAMEWORK_STRUCTURE_FUNCTIONS.has(callee.object.name);
    }
    return false;
}
