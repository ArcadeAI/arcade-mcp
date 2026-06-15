import type { Rule } from 'eslint';
/**
 * Merges the listeners of an arbitrary number of ESLint-based rules
 *
 * The purpose of this helper function is to merge the behaviour of a
 * variable number of rules. An ESLint rule "listens to" node visits based
 * on a node selector. If the node selector matches, the listener then
 * invokes a callback to proceed further with the node being visited.
 *
 * It supports when multiple rules share the same listeners, e.g., 2 rules
 * listen to `CallExpression` node visits. They will be run one after the other.
 *
 * @param rules rules to merge
 * @returns the merge of the rules' listeners
 */
export declare function mergeRules(...rules: Rule.RuleListener[]): Rule.RuleListener;
