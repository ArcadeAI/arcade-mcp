import type estree from 'estree';
import ts from 'typescript';
import type { TSESLint, TSESTree } from '@typescript-eslint/utils';
import type { RequiredParserServices } from './parser-services.js';
import type { Rule } from 'eslint';
export type RuleContext = TSESLint.RuleContext<string, string[]>;
export declare function isArray(node: estree.Node, services: RequiredParserServices): boolean;
/**
 * TypeScript provides a set of utility types to facilitate type transformations.
 * @see https://www.typescriptlang.org/docs/handbook/utility-types.html
 */
export declare const UTILITY_TYPES: Set<string>;
/**
 * Checks if the provided node is a JS typed array like "BigInt64Array". See TYPED_ARRAY_TYPES
 *
 * @param node
 * @param services
 * @returns
 */
export declare function isTypedArray(node: estree.Node, services: RequiredParserServices): boolean;
export declare function isString(node: estree.Node, services: RequiredParserServices): boolean;
export declare function isNumber(node: estree.Node, services: RequiredParserServices): boolean;
export declare function isBigIntType(type: ts.Type): boolean;
export declare function isNumberType(type: ts.Type): boolean;
export declare function isStringType(type: ts.Type): boolean;
export declare function isFunction(node: estree.Node, services: RequiredParserServices): boolean;
export declare function isUnion(node: estree.Node, services: RequiredParserServices): boolean;
export declare function isUndefinedOrNull(node: estree.Node, services: RequiredParserServices): boolean;
export declare function isThenable(node: estree.Node, services: RequiredParserServices): boolean;
/**
 * Checks if a node's type is either:
 * - Thenable (Promise-like), OR
 * - A union where ALL members are either thenable or "nothing" types (void, undefined, null)
 *
 * This is useful for rules like S3735 that allow voiding Promise operations,
 * including cases like optional chaining (Promise<T> | undefined) or
 * optional async callbacks (() => void | Promise<void>).
 */
export declare function isThenableOrVoidUnion(node: estree.Node, services: RequiredParserServices): boolean;
export declare function isAny(type: ts.Type): boolean;
/**
 * Checks if a node has a generic type like:
 *
 * function foo<T> (bar: T) {
 *    bar // is generic
 * }
 *
 * @param node TSESTree.Node
 * @param services RuleContext.parserServices
 * @returns
 */
export declare function isGenericType(node: TSESTree.Node, services: RequiredParserServices): boolean;
export declare function getTypeFromTreeNode(node: estree.Node, services: RequiredParserServices): ts.Type;
export declare function getTypeAsString(node: estree.Node, services: RequiredParserServices): string;
export declare function getSymbolAtLocation(node: estree.Node, services: RequiredParserServices): ts.Symbol | undefined;
export declare function getSignatureFromCallee(node: estree.Node, services: RequiredParserServices): ts.Signature | undefined;
/**
 * This function checks if a type may correspond to an array type. Beyond simple array types, it will also
 * consider the union of array types and generic types extending an array type.
 * @param type A type to check
 * @param services The services used to get access to the TypeScript type checker
 */
export declare function isArrayLikeType(type: ts.Type, services: RequiredParserServices): boolean;
/**
 * Test if the provided type is an array of strings.
 * @param type A TypeScript type.
 * @param services The services used to get access to the TypeScript type checker
 */
export declare function isStringArray(type: ts.Type, services: RequiredParserServices): boolean;
/**
 * Test if the provided type is an array of numbers.
 * @param type A TypeScript type.
 * @param services The services used to get access to the TypeScript type checker
 */
export declare function isNumberArray(type: ts.Type, services: RequiredParserServices): boolean;
/**
 * Test if the provided type is an array of big integers.
 * @param type A TypeScript type.
 * @param services The services used to get access to the TypeScript type checker
 */
export declare function isBigIntArray(type: ts.Type, services: RequiredParserServices): boolean;
/**
 * Checks whether a TypeScript type node denotes a type alias.
 * @param node a type node to check
 * @param context the rule context
 */
export declare function isTypeAlias(node: TSESTree.TypeNode, context: Rule.RuleContext): boolean | undefined;
export declare function isBooleanTrueType(type: ts.Type): boolean;
export declare function isBooleanType({ flags }: ts.Type): number;
export declare function isNullOrUndefinedType({ flags }: ts.Type): number;
export declare function isObjectType({ flags }: ts.Type): number;
export declare function typeHasMethod(node: estree.Node, methodName: string, services: RequiredParserServices): boolean;
/**
 * Checks if a type is iterable (can be used in for-of loops).
 * @param node The node to check
 * @param services The parser services
 * @returns true if the type is iterable, false otherwise
 */
export declare function isIterable(node: estree.Node, services: RequiredParserServices): boolean;
/**
 * Gets the number of parameters for a function-typed node using TypeScript type information.
 * Returns null if the parameter count cannot be determined.
 *
 * For functions with multiple call signatures (overloads), returns the maximum
 * parameter count across all signatures.
 *
 * @param node The node to get parameter count for
 * @param services TypeScript parser services
 * @returns The parameter count, or null if it cannot be determined
 */
export declare function getFunctionParameterCount(node: estree.Node, services: RequiredParserServices): number | null;
