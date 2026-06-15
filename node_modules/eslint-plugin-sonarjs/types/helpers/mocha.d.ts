import type estree from 'estree';
export interface TestCase {
    node: estree.Node;
    callback: estree.Function;
}
export declare function isTestConstruct(node: estree.Node, constructs?: string[]): boolean;
export declare function extractTestCase(node: estree.Node): TestCase | null;
/**
 * returns true if the node is a test case
 *
 * @param node
 * @returns
 */
export declare function isTestCase(node: estree.Node): boolean;
/**
 * returns true if the node is a describe block
 *
 * @param node
 * @returns
 */
export declare function isDescribeCase(node: estree.Node): boolean;
