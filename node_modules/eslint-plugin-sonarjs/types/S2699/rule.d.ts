import type { Rule } from 'eslint';
/**
 * We assume that the user is using a single assertion library per file,
 * this is why we are not saving if an assertion has been performed for
 * libX and the imported library was libY.
 */
export declare const rule: Rule.RuleModule;
