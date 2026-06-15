"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.getManifestsSanitizePaths = exports.getManifests = void 0;
const files_js_1 = require("../files.js");
const index_js_1 = require("./index.js");
const all_in_parent_dirs_js_1 = require("../find-up/all-in-parent-dirs.js");
/**
 * Returns the project manifests that are used to resolve the dependencies imported by
 * the module named `filename`, up to the passed working directory.
 */
const getManifests = (dir, topDir, fileSystem) => {
    const files = all_in_parent_dirs_js_1.patternInParentsCache
        .get(index_js_1.PACKAGE_JSON, fileSystem)
        .get(topDir ?? files_js_1.ROOT_PATH)
        .get(dir);
    return files.map(file => {
        const content = file.content;
        try {
            return JSON.parse((0, files_js_1.stripBOM)(content.toString()));
        }
        catch (error) {
            console.debug(`Error parsing package.json ${file.path}: ${error}`);
            return {};
        }
    });
};
exports.getManifests = getManifests;
const getManifestsSanitizePaths = (context, fileSystem) => {
    return (0, exports.getManifests)((0, files_js_1.dirnamePath)((0, files_js_1.normalizeToAbsolutePath)(context.filename)), (0, files_js_1.normalizeToAbsolutePath)(context.cwd), fileSystem);
};
exports.getManifestsSanitizePaths = getManifestsSanitizePaths;
