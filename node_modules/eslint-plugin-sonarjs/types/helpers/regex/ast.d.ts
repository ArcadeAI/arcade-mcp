import type estree from 'estree';
import type { RequiredParserServices } from '../parser-services.js';
export declare function isRegExpConstructor(node: estree.Node): node is estree.CallExpression;
export declare function isStringReplaceCall(call: estree.CallExpression, services: RequiredParserServices): boolean;
export declare function isStringRegexMethodCall(call: estree.CallExpression, services: RequiredParserServices): boolean;
