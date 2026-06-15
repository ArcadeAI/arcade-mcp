import type { TSESTree } from '@typescript-eslint/utils';
import type { Rule, SourceCode } from 'eslint';
import type { Node } from 'estree';
import type ts from 'typescript';
export declare function findFirstMatchingLocalAncestor(node: TSESTree.Node, predicate: (node: TSESTree.Node) => boolean): TSESTree.Node | undefined;
export declare function findFirstMatchingAncestor(node: TSESTree.Node, predicate: (node: TSESTree.Node) => boolean): TSESTree.Node | undefined;
export declare function localAncestorsChain(node: TSESTree.Node): TSESTree.Node[];
export declare function ancestorsChain(node: TSESTree.Node, boundaryTypes: Set<string>): TSESTree.Node[];
export declare function getParent(context: Rule.RuleContext, node: Node): import("estree").MethodDefinition | import("estree").Property | import("estree").CatchClause | import("estree").ClassDeclaration | import("estree").ClassExpression | import("estree").ClassBody | import("estree").FunctionExpression | import("estree").ArrowFunctionExpression | import("estree").Identifier | import("estree").SimpleLiteral | import("estree").RegExpLiteral | import("estree").BigIntLiteral | import("estree-jsx").JSXElement | import("estree-jsx").JSXFragment | import("estree").ArrayExpression | import("estree").AssignmentExpression | import("estree").AwaitExpression | import("estree").BinaryExpression | import("estree").SimpleCallExpression | import("estree").NewExpression | import("estree").ChainExpression | import("estree").ConditionalExpression | import("estree").ImportExpression | import("estree").LogicalExpression | import("estree").MemberExpression | import("estree").MetaProperty | import("estree").ObjectExpression | import("estree").SequenceExpression | import("estree").TaggedTemplateExpression | import("estree").TemplateLiteral | import("estree").ThisExpression | import("estree").UnaryExpression | import("estree").UpdateExpression | import("estree").YieldExpression | import("estree").FunctionDeclaration | import("estree").ImportDeclaration | import("estree").ExportNamedDeclaration | import("estree").ExportDefaultDeclaration | import("estree").ExportAllDeclaration | import("estree").ImportSpecifier | import("estree").ImportDefaultSpecifier | import("estree").ImportNamespaceSpecifier | import("estree").ExportSpecifier | import("estree").ObjectPattern | import("estree").ArrayPattern | import("estree").RestElement | import("estree").AssignmentPattern | import("estree").PrivateIdentifier | import("estree").Program | import("estree").PropertyDefinition | import("estree").SpreadElement | import("estree").ExpressionStatement | import("estree").BlockStatement | import("estree").StaticBlock | import("estree").EmptyStatement | import("estree").DebuggerStatement | import("estree").WithStatement | import("estree").ReturnStatement | import("estree").LabeledStatement | import("estree").BreakStatement | import("estree").ContinueStatement | import("estree").IfStatement | import("estree").SwitchStatement | import("estree").ThrowStatement | import("estree").TryStatement | import("estree").WhileStatement | import("estree").DoWhileStatement | import("estree").ForStatement | import("estree").ForInStatement | import("estree").ForOfStatement | import("estree").VariableDeclaration | import("estree").Super | import("estree").SwitchCase | import("estree").TemplateElement | import("estree").VariableDeclarator | import("estree-jsx").JSXIdentifier | import("estree-jsx").JSXNamespacedName | import("estree-jsx").JSXMemberExpression | import("estree-jsx").JSXEmptyExpression | import("estree-jsx").JSXExpressionContainer | import("estree-jsx").JSXSpreadAttribute | import("estree-jsx").JSXAttribute | import("estree-jsx").JSXOpeningElement | import("estree-jsx").JSXOpeningFragment | import("estree-jsx").JSXClosingElement | import("estree-jsx").JSXClosingFragment | import("estree-jsx").JSXText | undefined;
/**
 * Returns the parent of an ESLint node
 *
 * This function assumes that an ESLint node exposes a parent property,
 * which is always defined. However, it's better to use `getParent` if
 * it is possible to retrieve the parent based on the rule context.
 *
 * It should eventually disappear once we come up with a proper solution
 * against the conflicting typings between ESLint and TypeScript ESLint
 * when it comes to the parent of a node.
 *
 * @param node an ESLint node
 * @returns the parent node
 */
export declare function getNodeParent(node: Node): Node;
/**
 * Returns the direct children of a node
 * @param node the node to get the children
 * @param visitorKeys the visitor keys provided by the source code
 * @returns the node children
 */
export declare function childrenOf(node: Node, visitorKeys: SourceCode.VisitorKeys): Node[];
export declare function isTsAncestor(candidate: ts.Node, node: ts.Node): boolean;
