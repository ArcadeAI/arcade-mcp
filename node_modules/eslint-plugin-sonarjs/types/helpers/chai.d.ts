import type { Rule } from 'eslint';
import type estree from 'estree';
import type { ParserServicesWithTypeInformation } from '@typescript-eslint/utils';
import ts from 'typescript';
export declare function isImported(context: Rule.RuleContext): boolean;
export declare function isTSAssertion(services: ParserServicesWithTypeInformation, node: ts.Node): boolean;
export declare function isAssertion(context: Rule.RuleContext, node: estree.Node): boolean;
