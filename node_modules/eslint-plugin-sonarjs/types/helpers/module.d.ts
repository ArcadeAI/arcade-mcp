import type { Rule, Scope } from 'eslint';
import type estree from 'estree';
import { type Node } from './ast.js';
/**
 * Checks if the current file is an ES module based on sourceType.
 *
 * The parser sets sourceType based on file extension (.mjs/.cjs),
 * package.json "type" field, and ESLint configuration.
 */
export declare function isESModule(context: Rule.RuleContext): boolean;
export declare function getImportDeclarations(context: Rule.RuleContext): estree.ImportDeclaration[];
export declare function getRequireCalls(context: Rule.RuleContext): estree.CallExpression[];
export declare function isRequire(node: Node): node is estree.CallExpression;
/**
 * Returns the fully qualified name of ESLint node
 *
 * This function filters out the `node:` prefix
 *
 * A fully qualified name here denotes a value that is accessed through an imported
 * symbol, e.g., `foo.bar.baz` where `foo` was imported either from a require call
 * or an import statement:
 *
 * ```
 * const foo = require('lib');
 * foo.bar.baz.qux; // matches the fully qualified name 'lib.bar.baz.qux' (not 'foo.bar.baz.qux')
 * const foo2 = require('lib').bar;
 * foo2.baz.qux; // matches the fully qualified name 'lib.bar.baz.qux'
 * ```
 *
 * Returns null when an FQN could not be found.
 *
 * @param context the rule context
 * @param node the node
 * @param fqn the already traversed FQN (for recursive calls)
 * @param scope scope to look for the variable definition, used in recursion not to
 *              loop over same variable always in the lower scope
 */
export declare function getFullyQualifiedName(context: Rule.RuleContext, node: estree.Node, fqn?: string[], scope?: Scope.Scope): string | null;
/**
 * Removes `node:` prefix if such exists
 *
 * Node.js builtin modules can be referenced with a `node:` prefix (eg.: node:fs/promises)
 *
 * https://nodejs.org/api/esm.html#node-imports
 *
 * @param fqn Fully Qualified Name (ex.: `node:https.request`)
 * @returns `fqn` sanitized from `node:` prefix (ex.: `https.request`)
 */
export declare function removeNodePrefixIfExists(fqn: string | null): string | null;
/**
 * Helper function for getFullyQualifiedName to handle Member expressions
 * filling in the FQN array with the accessed properties.
 * @param node the Node to traverse
 * @param fqn the array with the qualifiers
 */
export declare function reduceToIdentifier(node: estree.Node, fqn?: string[]): estree.Node;
