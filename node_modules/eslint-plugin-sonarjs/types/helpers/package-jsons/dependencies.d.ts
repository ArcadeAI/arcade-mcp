import type { Rule } from 'eslint';
import { ComputedCache } from '../cache.js';
import type { Minimatch } from 'minimatch';
import { type NormalizedAbsolutePath } from '../files.js';
export type ModuleType = 'module' | 'commonjs';
/**
 * Cache for the available dependencies by dirname. Exported for tests
 */
export declare const dependenciesCache: ComputedCache<NormalizedAbsolutePath, Set<string | Minimatch>, NormalizedAbsolutePath>;
/**
 * Cache for module type signal by dirname. Exported for tests.
 */
export declare const moduleTypeCache: ComputedCache<NormalizedAbsolutePath, ModuleType | undefined, NormalizedAbsolutePath>;
/**
 * Retrieve the dependencies of all the package.json files available for the given file.
 *
 * @param dir dirname of the context.filename
 * @param topDir working dir, will search up to that root
 * @returns Set with the dependency names
 */
export declare function getDependencies(dir: NormalizedAbsolutePath, topDir: NormalizedAbsolutePath): Set<string | Minimatch>;
/**
 * Retrieve the module type signal for a file.
 *
 * Extension-specific module kinds (.mjs/.mts and .cjs/.cts) are explicit and
 * take precedence. Otherwise, package.json#type from the closest manifest only
 * is used. If that closest manifest exists but omits "type", default to CommonJS.
 */
export declare function getModuleType(filePath: NormalizedAbsolutePath, topDir: NormalizedAbsolutePath): ModuleType | undefined;
export declare function getDependenciesSanitizePaths(context: Rule.RuleContext): Set<string | Minimatch>;
/**
 * Gets the React version from the closest package.json.
 *
 * @param context ESLint rule context
 * @returns React version string (coerced from range) or null if not found
 */
export declare function getReactVersion(context: Rule.RuleContext): string | null;
/**
 * Parses a React version string and returns a valid semver version.
 * Exported for testing purposes.
 *
 * @param reactVersion Version string from package.json (e.g., "^18.0.0", "19.0", "catalog:frontend")
 * @returns Valid semver version string or null if parsing fails
 */
export declare function parseReactVersion(reactVersion: string): string | null;
export declare function getTypeScriptSignalsFromPackageJsonFiles(packageJsonFiles: Iterable<{
    content: string | Buffer;
}>): {
    typeScriptVersionSignals: string[];
    hasTypeScriptNativePreview: boolean;
};
/**
 * Gets a Node.js version signal from the package.json at baseDir.
 * Checks @types/node in all dependency fields first, then engines.node.
 * Returns the raw version string for further parsing.
 *
 * @param baseDir project base directory containing package.json
 * @returns raw version string from @types/node or engines.node, or null if not found
 */
export declare function getNodeVersionSignal(baseDir: NormalizedAbsolutePath): string | null;
/**
 * Gets a TypeScript version signal from the package.json at baseDir.
 * Checks dependency fields for "typescript" and returns the raw version range.
 *
 * @param baseDir project base directory containing package.json
 * @returns raw version string from typescript dependency, or null if not found
 */
export declare function getTypeScriptVersionSignal(baseDir: NormalizedAbsolutePath): string | null;
