"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.moduleTypeCache = exports.dependenciesCache = void 0;
exports.getDependencies = getDependencies;
exports.getModuleType = getModuleType;
exports.getDependenciesSanitizePaths = getDependenciesSanitizePaths;
exports.getReactVersion = getReactVersion;
exports.parseReactVersion = parseReactVersion;
exports.getTypeScriptSignalsFromPackageJsonFiles = getTypeScriptSignalsFromPackageJsonFiles;
exports.getNodeVersionSignal = getNodeVersionSignal;
exports.getTypeScriptVersionSignal = getTypeScriptVersionSignal;
const cache_js_1 = require("../cache.js");
const node_fs_1 = __importDefault(require("node:fs"));
const posix_1 = require("node:path/posix");
const semver_1 = require("semver");
const files_js_1 = require("../files.js");
const parse_js_1 = require("./parse.js");
const closest_js_1 = require("./closest.js");
const all_in_parent_dirs_js_1 = require("./all-in-parent-dirs.js");
const MODULE_TYPE_BY_EXTENSION = {
    '.mjs': 'module',
    '.mts': 'module',
    '.cjs': 'commonjs',
    '.cts': 'commonjs',
};
/**
 * Cache for the available dependencies by dirname. Exported for tests
 */
exports.dependenciesCache = new cache_js_1.ComputedCache((dir, topDir) => {
    const closestPackageJSONDirName = (0, closest_js_1.getClosestPackageJSONDir)(dir, topDir);
    const result = new Set();
    if (closestPackageJSONDirName) {
        for (const manifest of (0, all_in_parent_dirs_js_1.getManifests)(closestPackageJSONDirName, topDir, node_fs_1.default)) {
            const manifestDependencies = (0, parse_js_1.getDependenciesFromPackageJson)(manifest);
            for (const dependency of manifestDependencies) {
                result.add(dependency.name);
            }
        }
    }
    return result;
});
/**
 * Cache for module type signal by dirname. Exported for tests.
 */
exports.moduleTypeCache = new cache_js_1.ComputedCache((dir, topDir) => {
    const closestPackageJSONDirName = (0, closest_js_1.getClosestPackageJSONDir)(dir, topDir);
    if (!closestPackageJSONDirName) {
        return undefined;
    }
    const [firstManifest] = (0, all_in_parent_dirs_js_1.getManifests)(closestPackageJSONDirName, topDir, node_fs_1.default);
    if (firstManifest?.type === 'module' || firstManifest?.type === 'commonjs') {
        return firstManifest.type;
    }
    if (firstManifest) {
        return 'commonjs';
    }
    return undefined;
});
/**
 * Retrieve the dependencies of all the package.json files available for the given file.
 *
 * @param dir dirname of the context.filename
 * @param topDir working dir, will search up to that root
 * @returns Set with the dependency names
 */
function getDependencies(dir, topDir) {
    const closestPackageJSONDirName = (0, closest_js_1.getClosestPackageJSONDir)(dir, topDir);
    if (closestPackageJSONDirName) {
        return exports.dependenciesCache.get(closestPackageJSONDirName, topDir);
    }
    return new Set();
}
/**
 * Retrieve the module type signal for a file.
 *
 * Extension-specific module kinds (.mjs/.mts and .cjs/.cts) are explicit and
 * take precedence. Otherwise, package.json#type from the closest manifest only
 * is used. If that closest manifest exists but omits "type", default to CommonJS.
 */
function getModuleType(filePath, topDir) {
    const extensionSignal = MODULE_TYPE_BY_EXTENSION[(0, posix_1.extname)(filePath).toLowerCase()];
    if (extensionSignal) {
        return extensionSignal;
    }
    return exports.moduleTypeCache.get((0, files_js_1.dirnamePath)(filePath), topDir);
}
function getDependenciesSanitizePaths(context) {
    return getDependencies((0, files_js_1.dirnamePath)((0, files_js_1.normalizeToAbsolutePath)(context.filename)), (0, files_js_1.normalizeToAbsolutePath)(context.cwd));
}
/**
 * Gets the React version from the closest package.json.
 *
 * @param context ESLint rule context
 * @returns React version string (coerced from range) or null if not found
 */
function getReactVersion(context) {
    const dir = (0, files_js_1.dirnamePath)((0, files_js_1.normalizeToAbsolutePath)(context.filename));
    for (const packageJson of (0, all_in_parent_dirs_js_1.getManifests)(dir, (0, files_js_1.normalizeToAbsolutePath)(context.cwd), node_fs_1.default)) {
        const reactVersion = packageJson.dependencies?.react ?? packageJson.devDependencies?.react;
        if (reactVersion) {
            const parsed = parseReactVersion(reactVersion);
            if (parsed) {
                return parsed;
            }
            // Continue searching in parent package.json files if parsing fails
        }
    }
    return null;
}
/**
 * Parses a React version string and returns a valid semver version.
 * Exported for testing purposes.
 *
 * @param reactVersion Version string from package.json (e.g., "^18.0.0", "19.0", "catalog:frontend")
 * @returns Valid semver version string or null if parsing fails
 */
function parseReactVersion(reactVersion) {
    try {
        // Coerce version ranges (e.g., "^18.0.0") to valid semver versions
        return (0, semver_1.minVersion)(reactVersion)?.version ?? null;
    }
    catch {
        // Handle non-semver strings like pnpm catalog references (e.g., "catalog:frontend")
        return null;
    }
}
function getAllDependencySignals(packageJson) {
    return {
        ...packageJson.dependencies,
        ...packageJson.devDependencies,
        ...packageJson.peerDependencies,
        ...packageJson.optionalDependencies,
    };
}
function getDependencyVersionSignal(packageJson, dependencyName) {
    const dependencyVersion = getAllDependencySignals(packageJson)[dependencyName];
    return typeof dependencyVersion === 'string' ? dependencyVersion : null;
}
function getVersionSignalFromManifests(baseDir, dependencyName, fallbackSignal) {
    const [packageJson] = (0, all_in_parent_dirs_js_1.getManifests)(baseDir, baseDir, node_fs_1.default);
    if (!packageJson) {
        return null;
    }
    const dependencyVersion = getDependencyVersionSignal(packageJson, dependencyName);
    if (isValidDependencySignal(dependencyVersion)) {
        return dependencyVersion;
    }
    const fallbackVersion = fallbackSignal?.(packageJson);
    if (fallbackVersion !== null && fallbackVersion !== undefined) {
        return fallbackVersion;
    }
    return null;
}
function isValidDependencySignal(versionSignal) {
    return versionSignal !== null && versionSignal !== 'latest' && versionSignal !== '*';
}
function hasTypeScriptNativePreviewSignal(packageJson) {
    return isValidDependencySignal(getDependencyVersionSignal(packageJson, '@typescript/native-preview'));
}
function getTypeScriptVersionSignalsFromPackageJson(packageJson) {
    const result = [];
    const nativePreviewVersion = getDependencyVersionSignal(packageJson, '@typescript/native-preview');
    if (isValidDependencySignal(nativePreviewVersion)) {
        result.push(nativePreviewVersion);
    }
    const typeScriptVersion = getDependencyVersionSignal(packageJson, 'typescript');
    if (isValidDependencySignal(typeScriptVersion)) {
        result.push(typeScriptVersion);
    }
    return result;
}
function getTypeScriptSignalsFromPackageJsonFiles(packageJsonFiles) {
    const typeScriptVersionSignals = [];
    let hasTypeScriptNativePreview = false;
    for (const packageJsonFile of packageJsonFiles) {
        const packageJson = parsePackageJsonContent(packageJsonFile.content);
        if (packageJson === undefined) {
            continue;
        }
        typeScriptVersionSignals.push(...getTypeScriptVersionSignalsFromPackageJson(packageJson));
        hasTypeScriptNativePreview =
            hasTypeScriptNativePreview || hasTypeScriptNativePreviewSignal(packageJson);
    }
    return { typeScriptVersionSignals, hasTypeScriptNativePreview };
}
/**
 * Gets a Node.js version signal from the package.json at baseDir.
 * Checks @types/node in all dependency fields first, then engines.node.
 * Returns the raw version string for further parsing.
 *
 * @param baseDir project base directory containing package.json
 * @returns raw version string from @types/node or engines.node, or null if not found
 */
function getNodeVersionSignal(baseDir) {
    return getVersionSignalFromManifests(baseDir, '@types/node', packageJson => {
        const enginesNode = packageJson.engines?.['node'];
        return typeof enginesNode === 'string' ? enginesNode : null;
    });
}
/**
 * Gets a TypeScript version signal from the package.json at baseDir.
 * Checks dependency fields for "typescript" and returns the raw version range.
 *
 * @param baseDir project base directory containing package.json
 * @returns raw version string from typescript dependency, or null if not found
 */
function getTypeScriptVersionSignal(baseDir) {
    return getVersionSignalFromManifests(baseDir, 'typescript');
}
function parsePackageJsonContent(content) {
    const packageJsonContent = typeof content === 'string' ? content : content.toString();
    try {
        return JSON.parse((0, files_js_1.stripBOM)(packageJsonContent));
    }
    catch {
        return undefined;
    }
}
