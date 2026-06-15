type Default = string | boolean | number | string[] | number[] | Object;
type ESLintConfigurationDefaultProperty = {
    default: Default;
};
/**
 * Necessary for the property to show up in the SonarQube interface.
 * @param description will explain to the user what the property configures
 * @param displayName only necessary if the name of the property is different from the `field` name
 * @param customDefault only necessary if different default in SQ different than in JS/TS
 * @param items only necessary if type is 'array'
 * @param fieldType only necessary if you need to override the default fieldType in SQ
 * @param customForConfiguration replacement content how to pass this variable to the Configuration object
 */
export type ESLintConfigurationSQProperty = ESLintConfigurationDefaultProperty & {
    description: string;
    displayName?: string;
    customDefault?: Default;
    items?: {
        type: 'string' | 'integer';
    };
    fieldType?: 'TEXT';
    customForConfiguration?: (value: unknown) => unknown;
};
export type ESLintConfigurationProperty = ESLintConfigurationDefaultProperty | ESLintConfigurationSQProperty;
type ESLintConfigurationNamedProperty = ESLintConfigurationProperty & {
    field: string;
};
type ESLintConfigurationElement = ESLintConfigurationNamedProperty[] | ESLintConfigurationProperty;
export type ESLintConfiguration = ESLintConfigurationElement[];
export declare function defaultOptions(configuration?: ESLintConfiguration): Default[] | undefined;
/**
 * Applies `customForConfiguration` transformations to merged configuration values.
 *
 * When SonarQube sends rule parameters, the values may not match what the underlying
 * ESLint rule expects. For example, S1441 (quotes) exposes a boolean `singleQuotes`
 * property in SonarQube, but the ESLint rule expects the string `"single"` or `"double"`.
 * The `customForConfiguration` function on a field definition bridges this gap.
 *
 * This function walks the `mergedValues` array (the result of merging default options
 * with user-provided configurations) and applies any `customForConfiguration` transform
 * found in the corresponding `fields` element. It handles both configuration patterns:
 *
 * - **Primitive elements** (e.g., S1441's boolean → string mapping): the transform is
 *   called directly on the merged value.
 * - **Object elements** (e.g., S6418's `randomnessSensibility` string → number): each
 *   named property within the object is checked individually, and only properties that
 *   define `customForConfiguration` are transformed.
 *
 * Values without a corresponding field definition or without `customForConfiguration`
 * are passed through unchanged.
 *
 * @param fields - The rule's field definitions from its `config.ts` (may contain transforms)
 * @param mergedValues - The merged configuration array (defaults + user overrides)
 * @returns A new array with transformed values ready to pass to the ESLint rule
 *
 * @example
 * // S1441: primitive transform (boolean → string)
 * // fields[0] has customForConfiguration: (v) => v ? 'single' : 'double'
 * applyTransformations(fields, [true, {avoidEscape: true}])
 * // → ['single', {avoidEscape: true}]
 *
 * @example
 * // S6418: object property transform (string → number)
 * // fields[0][1] has customForConfiguration: (v) => Number(v)
 * applyTransformations(fields, [{secretWords: 'api_key', randomnessSensibility: '5.0'}])
 * // → [{secretWords: 'api_key', randomnessSensibility: 5}]
 */
export declare function applyTransformations(fields: ESLintConfiguration | undefined, mergedValues: unknown[] | undefined): unknown[];
export {};
