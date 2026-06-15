import type estree from 'estree';
/**
 * Test framework structural functions whose callbacks define test structure
 * rather than business logic. Covers: Mocha, Jest, Vitest, Jasmine, Node.js test runner.
 */
export declare const TEST_FRAMEWORK_STRUCTURE_FUNCTIONS: Set<string>;
/**
 * Checks if a CallExpression is a test framework structural function.
 * Handles both direct calls (describe()) and member expressions (describe.only()).
 */
export declare function isTestFrameworkCall(node: estree.Node): boolean;
