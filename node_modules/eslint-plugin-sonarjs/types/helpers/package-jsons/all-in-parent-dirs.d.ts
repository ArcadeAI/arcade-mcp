import type { Filesystem } from '../find-up/find-minimatch.js';
import type { PackageJson } from 'type-fest';
import { type NormalizedAbsolutePath } from '../files.js';
import type { Rule } from 'eslint';
/**
 * Returns the project manifests that are used to resolve the dependencies imported by
 * the module named `filename`, up to the passed working directory.
 */
export declare const getManifests: (dir: NormalizedAbsolutePath, topDir?: NormalizedAbsolutePath, fileSystem?: Filesystem) => Array<PackageJson>;
export declare const getManifestsSanitizePaths: (context: Rule.RuleContext, fileSystem?: Filesystem) => Array<PackageJson>;
