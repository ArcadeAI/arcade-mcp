/**
 * This is the entry point of the ESLint Plugin.
 * Said differently, this is the public API of the ESLint Plugin.
 */
import type { ESLint, Linter } from 'eslint';
export declare const configs: {
    recommended: Linter.FlatConfig;
    'recommended-legacy': Linter.LegacyConfig;
};
/**
 * I kept the meta export for compatibility, but we need to find a way to populate it without relying on the package manifest
 */
export declare const meta: {
    name: string;
    version: string;
};
declare const plugin: ESLint.Plugin;
export default plugin;
export { rules } from './plugin-rules.js';
