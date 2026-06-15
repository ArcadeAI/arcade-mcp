"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ROOT_PATH = void 0;
exports.stripBOM = stripBOM;
exports.normalizePath = normalizePath;
exports.normalizeToAbsolutePath = normalizeToAbsolutePath;
exports.isRoot = isRoot;
exports.isAbsolutePath = isAbsolutePath;
exports.dirnamePath = dirnamePath;
exports.joinPaths = joinPaths;
exports.basenamePath = basenamePath;
/*
 * SonarQube JavaScript Plugin
 * Copyright (C) SonarSource Sàrl
 * mailto:info AT sonarsource DOT com
 *
 * You can redistribute and/or modify this program under the terms of
 * the Sonar Source-Available License Version 1, as published by SonarSource Sàrl.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the Sonar Source-Available License for more details.
 *
 * You should have received a copy of the Sonar Source-Available License
 * along with this program; if not, see https://sonarsource.com/license/ssal/
 */
const posix_1 = require("node:path/posix");
const win32_1 = require("node:path/win32");
/**
 * Root path constant for Unix filesystem
 */
exports.ROOT_PATH = '/';
/**
 * Byte Order Marker
 */
const BOM_BYTE = 0xfeff;
const isWindows = process.platform === 'win32';
/**
 * Removes any Byte Order Marker (BOM) from a string's head
 *
 * A string's head is nothing else but its first character.
 *
 * @param str the input string
 * @returns the stripped string
 */
function stripBOM(str) {
    if (str.codePointAt(0) === BOM_BYTE) {
        return str.slice(1);
    }
    return str;
}
/**
 * Normalizes a path to Unix format (forward slashes).
 * For absolute paths on Windows, resolves them to ensure they have a drive letter.
 * For relative paths, only converts slashes without resolving.
 * Cross-platform behavior:
 * - On Windows: all absolute paths are resolved with win32 to add drive letter
 * - On Linux: paths are only converted (slashes), no resolution needed
 * @param filePath the path to normalize
 * @returns the normalized path as a branded UnixPath type
 */
function normalizePath(filePath) {
    if (isWindows && isAbsolutePath(filePath)) {
        // On Windows, resolve to add drive letter if missing
        filePath = (0, win32_1.resolve)(filePath);
    }
    return toUnixPath(filePath);
}
/**
 * Normalizes a path to an absolute Unix format.
 * Guarantees the returned path is absolute.
 * @param filePath the path to normalize
 * @param baseDir base directory to resolve relative paths against
 * @returns the normalized path as a branded AbsoluteUnixPath type
 */
function normalizeToAbsolutePath(filePath, baseDir = exports.ROOT_PATH) {
    if (isAbsolutePath(filePath)) {
        // On Windows, resolve to add drive letter if missing
        filePath = (0, win32_1.resolve)(filePath);
    }
    else {
        filePath = isWindows ? (0, win32_1.resolve)(baseDir, filePath) : (0, posix_1.resolve)(baseDir, filePath);
    }
    return toUnixPath(filePath);
}
function toUnixPath(filePath) {
    return filePath.replaceAll(/[\\/]+/g, '/');
}
function isParseResultRoot(result) {
    // A path is a root if it has a non-empty root and no base (filename)
    // and dir is either empty or equals the root itself
    return (result.root !== '' && result.base === '' && (result.dir === '' || result.dir === result.root));
}
function isRoot(file) {
    return isParseResultRoot((0, win32_1.parse)(file)) || isParseResultRoot((0, posix_1.parse)(file));
}
function isAbsolutePath(path) {
    // Check for Windows drive letter (e.g., 'c:', 'C:', 'D:')
    // Node's isAbsolute considers 'c:' as relative (drive-relative), but we treat it as absolute
    if (/^[a-zA-Z]:/.test(path)) {
        return true;
    }
    return (0, posix_1.isAbsolute)(path) || (0, win32_1.isAbsolute)(path);
}
/**
 * Type-safe dirname that preserves the NormalizedAbsolutePath brand.
 * The dirname of an absolute path is always absolute.
 * @param filePath the absolute path to get the directory of
 * @returns the parent directory as a branded NormalizedAbsolutePath
 */
function dirnamePath(filePath) {
    return (0, posix_1.dirname)(filePath);
}
/**
 * Type-safe path join that preserves the NormalizedAbsolutePath brand.
 * Joins path segments using posix separators.
 * @param base the base absolute path
 * @param segments additional path segments to join
 * @returns the joined path as a branded NormalizedAbsolutePath
 */
function joinPaths(base, ...segments) {
    return (0, posix_1.join)(base, ...segments);
}
/**
 * Type-safe basename that extracts the filename from a path.
 * @param filePath the path to extract the basename from
 * @returns the filename (last segment of the path)
 */
function basenamePath(filePath) {
    return (0, posix_1.basename)(filePath);
}
