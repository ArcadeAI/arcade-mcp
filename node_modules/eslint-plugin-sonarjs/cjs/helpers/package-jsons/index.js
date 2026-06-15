"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PACKAGE_JSON = void 0;
exports.isPackageJson = isPackageJson;
exports.fillPackageJsonCaches = fillPackageJsonCaches;
exports.clearDependenciesCache = clearDependenciesCache;
const find_minimatch_js_1 = require("../find-up/find-minimatch.js");
const dependencies_js_1 = require("./dependencies.js");
const closest_js_1 = require("../find-up/closest.js");
const all_in_parent_dirs_js_1 = require("../find-up/all-in-parent-dirs.js");
const posix_1 = require("node:path/posix");
exports.PACKAGE_JSON = 'package.json';
function isPackageJson(path) {
    return (0, posix_1.basename)(path).toLowerCase() === exports.PACKAGE_JSON;
}
function fillPackageJsonCaches(packageJsons, dirnameToParent, topDir) {
    const closestCache = closest_js_1.closestPatternCache.get(exports.PACKAGE_JSON).get(topDir);
    const allPackageJsonsCache = all_in_parent_dirs_js_1.patternInParentsCache.get(exports.PACKAGE_JSON).get(topDir);
    // We depend on the order of the paths, from parent-to-child paths (guaranteed by the use of a Map in the package-json store)
    for (const [dir, parent] of dirnameToParent) {
        const currentPackageJson = packageJsons.get(dir);
        closestCache.set(dir, currentPackageJson ?? (parent ? closestCache.get(parent) : undefined));
        const allPackageJsons = [];
        if (parent) {
            allPackageJsons.push(...allPackageJsonsCache.get(dir));
        }
        if (currentPackageJson) {
            allPackageJsons.push(currentPackageJson);
        }
        allPackageJsonsCache.set(dir, allPackageJsons);
    }
}
/**
 * In the case of SonarIDE, when a package.json file changes, the cache can become obsolete.
 */
function clearDependenciesCache() {
    dependencies_js_1.dependenciesCache.clear();
    dependencies_js_1.moduleTypeCache.clear();
    closest_js_1.closestPatternCache.get(exports.PACKAGE_JSON).clear();
    all_in_parent_dirs_js_1.patternInParentsCache.get(exports.PACKAGE_JSON).clear();
    find_minimatch_js_1.MinimatchCache.clear();
}
