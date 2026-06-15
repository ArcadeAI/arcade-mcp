import type { File, NormalizedAbsolutePath } from '../files.js';
export declare const PACKAGE_JSON = "package.json";
export declare function isPackageJson(path: NormalizedAbsolutePath): boolean;
export declare function fillPackageJsonCaches(packageJsons: Map<NormalizedAbsolutePath, File>, dirnameToParent: Map<NormalizedAbsolutePath, NormalizedAbsolutePath | undefined>, topDir: NormalizedAbsolutePath): void;
/**
 * In the case of SonarIDE, when a package.json file changes, the cache can become obsolete.
 */
export declare function clearDependenciesCache(): void;
