import type { Rule } from 'eslint';
import type estree from 'estree';
export declare function isInsideVueSetupScript(node: estree.Node, ctx: Rule.RuleContext): boolean;
