export interface StringLiteralToken {
    value: string;
    range: [number, number];
}
/**
 * Parse 's' and return array of tokens with range. We assume 's' is correctly terminated because it was already parsed
 * into AST.
 *
 * Inspired by https://github.com/ota-meshi/eslint-plugin-regexp/blob/61ae9424e0f3bde62569718b597cdc036fec9f71/lib/utils/string-literal-parser/tokenizer.ts
 */
export declare function tokenizeString(s: string): StringLiteralToken[];
