import type estree from 'estree';
import type { Rule } from 'eslint';
import type { RuleTextEdit } from '@eslint/core';
export declare function removeNodeWithLeadingWhitespaces(context: Rule.RuleContext, node: estree.Node, fixer: Rule.RuleFixer, removeUntil?: number): RuleTextEdit;
