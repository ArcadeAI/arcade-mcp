import type { AST } from 'eslint';
import type estree from 'estree';
import type * as regexpp from '@eslint-community/regexpp';
/**
 * Returns the location of regexpNode relative to the node, which is regexp string or literal. If the computation
 * of location fails, it returns the range of the whole node.
 */
export declare function getRegexpRange(node: estree.Node, regexpNode: regexpp.AST.Node): AST.Range;
