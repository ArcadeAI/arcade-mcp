"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.defaultOptions = defaultOptions;
exports.applyTransformations = applyTransformations;
function defaultOptions(configuration) {
    return configuration?.map(element => {
        if (Array.isArray(element)) {
            return Object.fromEntries(element.map(namedProperty => [namedProperty.field, namedProperty.default]));
        }
        else {
            return element.default;
        }
    });
}
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
function applyTransformations(fields, mergedValues) {
    if (!fields || !mergedValues) {
        return mergedValues ?? [];
    }
    // Walk mergedValues in parallel with fields. Each position in the array
    // corresponds to one element in the rule's config.ts `fields` definition.
    // For example, S1441 fields = [primitive, object]:
    //   mergedValues[0] = true          → fields[0] = { default: 'single', customForConfiguration: ... }
    //   mergedValues[1] = {avoidEscape} → fields[1] = [{field: 'avoidEscape', ...}, ...]
    return mergedValues.map((mergedConfigEntry, index) => {
        // Extra values beyond what fields defines (shouldn't happen, but safe to pass through)
        if (index >= fields.length) {
            return mergedConfigEntry;
        }
        const fieldDefinition = fields[index];
        if (Array.isArray(fieldDefinition)) {
            // ── Object config element ──
            // fieldDefinition is an array of named properties: [{field, default, ...}, ...]
            // mergedConfigEntry is an object: { fieldName: value, ... }
            //
            // Example — S6418 fields = [[ {field: 'secretWords', ...}, {field: 'randomnessSensibility', customForConfiguration: (v) => Number(v)} ]]
            // mergedConfigEntry = { secretWords: 'api_key', randomnessSensibility: '5.0' }
            // After transform: { secretWords: 'api_key', randomnessSensibility: 5 }
            if (mergedConfigEntry &&
                typeof mergedConfigEntry === 'object' &&
                !Array.isArray(mergedConfigEntry)) {
                const transformedEntry = { ...mergedConfigEntry };
                for (const propertyDef of fieldDefinition) {
                    // Only transform properties that define customForConfiguration and are present in the object
                    if ('customForConfiguration' in propertyDef &&
                        typeof propertyDef.customForConfiguration === 'function' &&
                        propertyDef.field in transformedEntry) {
                        transformedEntry[propertyDef.field] = propertyDef.customForConfiguration(transformedEntry[propertyDef.field]);
                    }
                }
                return transformedEntry;
            }
        }
        else if ('customForConfiguration' in fieldDefinition &&
            typeof fieldDefinition.customForConfiguration === 'function') {
            // ── Primitive config element with a transform ──
            // fieldDefinition is a single property: { default, customForConfiguration, ... }
            // mergedConfigEntry is a scalar value (string, number, boolean)
            //
            // Example — S1441 fieldDefinition = { default: 'single', customForConfiguration: (v) => ... }
            // mergedConfigEntry = 'true' (string from SQ)
            // After transform: 'single' (string expected by ESLint quotes rule)
            return fieldDefinition.customForConfiguration(mergedConfigEntry);
        }
        // No transform defined for this element — pass through unchanged.
        // This is the common case for most rules (e.g., S134 threshold, S100 format pattern).
        return mergedConfigEntry;
    });
}
