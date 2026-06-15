import type { Rule, Scope } from 'eslint';
import type estree from 'estree';
export declare const rule: Rule.RuleModule;
/**
 * for `x.foo = 42` returns 'x' variable and 'foo' property string
 */
export declare function getVariablePropertyFromAssignment(context: Rule.RuleContext, assignment: estree.AssignmentExpression): {
    objectVariable: Scope.Variable;
    property: string;
} | undefined;
