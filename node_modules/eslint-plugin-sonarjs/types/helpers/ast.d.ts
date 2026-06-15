import type { TSESTree } from '@typescript-eslint/utils';
import type { Rule, Scope } from 'eslint';
import type estree from 'estree';
export type Node = estree.Node | TSESTree.Node;
export type LoopLike = estree.WhileStatement | estree.DoWhileStatement | estree.ForStatement | estree.ForOfStatement | estree.ForInStatement;
export type FunctionNodeType = estree.FunctionDeclaration | estree.FunctionExpression | estree.ArrowFunctionExpression;
export type StringLiteral = estree.Literal & {
    value: string;
};
export declare const FUNCTION_NODES: string[];
export declare const functionLike: Set<string>;
export declare function isFunctionExpression(node: TSESTree.Node | undefined): node is TSESTree.FunctionExpression;
export declare function isFunctionDeclaration(node: TSESTree.Node | undefined): node is TSESTree.FunctionDeclaration;
export declare function isArrowFunctionExpression(node: TSESTree.Node | undefined): node is TSESTree.ArrowFunctionExpression;
export declare function isIdentifier(node: Node | undefined, ...values: string[]): node is estree.Identifier;
export declare function getProgramStatements(program: estree.Program): estree.Statement[];
export declare function isIfStatement(node: Node | undefined): node is TSESTree.IfStatement;
export declare function isMemberWithProperty(node: estree.Node, ...values: string[]): boolean;
export declare function isThrowStatement(node: Node | undefined): node is TSESTree.ThrowStatement;
export declare function isMemberExpression(node: estree.Node, objectValue: string, ...propertyValue: string[]): boolean;
export declare function isLogicalExpression(node: TSESTree.Node | undefined): node is TSESTree.LogicalExpression;
export declare function isBinaryPlus(node: estree.Node): node is estree.BinaryExpression & {
    operator: '+';
};
export declare function isArrayExpression(node: estree.Node | undefined): node is estree.ArrayExpression;
export declare function isRequireModule(node: estree.CallExpression, ...moduleNames: string[]): boolean;
export declare function isMethodInvocation(callExpression: estree.CallExpression, objectIdentifierName: string, methodName: string, minArgs: number): boolean;
export declare function isFunctionInvocation(callExpression: estree.CallExpression, functionName: string, minArgs: number): boolean;
export declare function isFunctionCall(node: estree.Node): node is estree.CallExpression & {
    callee: estree.Identifier;
};
export declare function isMethodCall(callExpr: estree.CallExpression): callExpr is estree.CallExpression & {
    callee: estree.MemberExpression & {
        property: estree.Identifier;
    };
};
export declare function isCallingMethod(callExpr: estree.CallExpression, arity: number, ...methodNames: string[]): callExpr is estree.CallExpression & {
    callee: estree.MemberExpression & {
        property: estree.Identifier;
    };
};
export declare function isModuleExports(node: estree.Node): boolean;
export declare function isFunctionNode(node: estree.Node): node is FunctionNodeType;
export declare function isLiteral(n: estree.Node | null): n is estree.Literal;
export declare function isNullLiteral(n: estree.Node): boolean;
export declare function isFalseLiteral(n: estree.Node): boolean;
export declare function isUndefined(node: Node): boolean;
/**
 * Detect expression statements like the following:
 *  myArray[1] = 42;
 *  myArray[1] += 42;
 *  myObj.prop1 = 3;
 *  myObj.prop1 += 3;
 */
export declare function isElementWrite(statement: estree.ExpressionStatement, ref: Scope.Reference, recursive?: boolean): boolean;
export declare function isReferenceTo(ref: Scope.Reference, node: estree.Node): boolean;
export declare function getUniqueWriteUsage(context: Rule.RuleContext, name: string, node: estree.Node): estree.Node | undefined;
export declare function getUniqueWriteReference(variable: Scope.Variable | undefined): estree.Node | undefined;
export declare function getUniqueWriteUsageOrNode(context: Rule.RuleContext, node: estree.Node, recursive?: boolean): estree.Node;
export declare function getValueOfExpression<T extends estree.Node['type']>(context: Rule.RuleContext, expr: estree.Node | undefined | null, type: T, recursive?: boolean): Extract<estree.Node, {
    type: T;
}> | undefined;
/**
 * for `x = 42` or `let x = 42` when visiting '42' returns 'x' variable
 */
export declare function getLhsVariable(context: Rule.RuleContext, node: estree.Node): Scope.Variable | undefined;
export declare function getVariableFromScope(scope: Scope.Scope | null, name: string): Scope.Variable | undefined;
export declare function getVariableFromName(context: Rule.RuleContext, name: string, node: estree.Node): Scope.Variable | undefined;
/**
 * Takes array of arguments. Keeps following variable definitions
 * and unpacking arrays as long as possible. Returns flattened
 * array with all collected nodes.
 *
 * A usage example should clarify why this might be useful.
 * According to ExpressJs `app.use` spec, the arguments can be:
 *
 * - A middleware function.
 * - A series of middleware functions (separated by commas).
 * - An array of middleware functions.
 * - A combination of all of the above.
 *
 * This means that methods like `app.use` accept variable arguments,
 * but also arrays, or combinations thereof. This methods helps
 * to flatten out such complicated composed argument lists.
 */
export declare function flattenArgs(context: Rule.RuleContext, args: estree.Node[]): estree.Node[];
export declare function resolveIdentifiers(node: TSESTree.Node, acceptShorthand?: boolean): TSESTree.Identifier[];
export declare function getPropertyWithValue(context: Rule.RuleContext, objectExpression: estree.ObjectExpression, propertyName: string, propertyValue: estree.Literal['value']): estree.Property | undefined;
/**
 * Retrieves the property with the specified key from the given node.
 * @returns The property if found, or null if not found, or undefined if property not found and one of the properties
 * is an unresolved SpreadElement.
 */
export declare function getProperty(expr: estree.Node | undefined | null, key: string, ctx: Rule.RuleContext): estree.Property | null | undefined;
export declare function resolveFromFunctionReference(context: Rule.RuleContext, functionIdentifier: estree.Identifier): estree.FunctionExpression | estree.FunctionDeclaration | null;
export declare function resolveFunction(context: Rule.RuleContext, node: estree.Node): estree.Function | null;
export declare function checkSensitiveCall(context: Rule.RuleContext, callExpression: estree.CallExpression, sensitiveArgumentIndex: number, sensitiveProperty: string, sensitivePropertyValue: boolean, message: string): void;
export declare function isStringLiteral(node: estree.Node): node is StringLiteral;
export declare function isBooleanLiteral(node: estree.Node): node is estree.Literal & {
    value: boolean;
};
export declare function isNumberLiteral(node: estree.Node): node is estree.Literal & {
    value: number;
};
export declare function isRegexLiteral(node: estree.Node): node is estree.RegExpLiteral;
/**
 * Checks if the node is of the form: foo.bar
 *
 * @param node
 * @returns
 */
export declare function isDotNotation(node: estree.Node): node is estree.MemberExpression & {
    property: estree.Identifier;
};
/**
 * Checks if the node is of the form: foo["bar"]
 *
 * @param node
 * @returns
 */
export declare function isIndexNotation(node: estree.Node): node is estree.MemberExpression & {
    property: StringLiteral;
};
export declare function isObjectDestructuring(node: estree.Node): node is (estree.VariableDeclarator & {
    id: estree.ObjectPattern;
}) | (estree.AssignmentExpression & {
    left: estree.ObjectPattern;
});
export declare function isStaticTemplateLiteral(node: estree.Node): node is estree.TemplateLiteral;
export declare function isSimpleRawString(node: estree.Node): node is estree.TaggedTemplateExpression;
export declare function getSimpleRawStringValue(node: estree.TaggedTemplateExpression): string;
export declare function isThisExpression(node: estree.Node): node is estree.ThisExpression;
export declare function isProperty(node: estree.Node): node is estree.Property;
/**
 * Check if an identifier has no known value, meaning:
 *
 * - It's not imported/required
 * - Defined variable without any write references (function parameter?)
 * - Non-defined variable (a possible global?)
 *
 * @param node Node to check
 * @param ctx Rule context
 */
export declare function isUnresolved(node: estree.Node | undefined | null, ctx: Rule.RuleContext): boolean;
export declare function hasParent(node: estree.Node): node is estree.Node & Rule.NodeParentExtension;
/**
 * Checks if a function node has a type predicate return type (`: x is Type`).
 */
export declare function hasTypePredicateReturn(node: estree.Node): boolean;
