export type NormalizedPath = string & {
    readonly __normalizedPathBrand: 'NormalizedPath';
};
export type NormalizedAbsolutePath = string & {
    readonly __normalizedAbsolutePathBrand: 'NormalizedAbsolutePath';
};
export type File = {
    readonly path: NormalizedAbsolutePath;
    readonly content: Buffer | string;
};
/**
 * Root path constant for Unix filesystem
 */
export declare const ROOT_PATH: NormalizedAbsolutePath;
/**
 * Removes any Byte Order Marker (BOM) from a string's head
 *
 * A string's head is nothing else but its first character.
 *
 * @param str the input string
 * @returns the stripped string
 */
export declare function stripBOM(str: string): string;
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
export declare function normalizePath(filePath: string): NormalizedPath;
/**
 * Normalizes a path to an absolute Unix format.
 * Guarantees the returned path is absolute.
 * @param filePath the path to normalize
 * @param baseDir base directory to resolve relative paths against
 * @returns the normalized path as a branded AbsoluteUnixPath type
 */
export declare function normalizeToAbsolutePath(filePath: string, baseDir?: NormalizedAbsolutePath): NormalizedAbsolutePath;
export declare function isRoot(file: string): boolean;
export declare function isAbsolutePath(path: string): boolean;
/**
 * Type-safe dirname that preserves the NormalizedAbsolutePath brand.
 * The dirname of an absolute path is always absolute.
 * @param filePath the absolute path to get the directory of
 * @returns the parent directory as a branded NormalizedAbsolutePath
 */
export declare function dirnamePath(filePath: NormalizedAbsolutePath): NormalizedAbsolutePath;
/**
 * Type-safe path join that preserves the NormalizedAbsolutePath brand.
 * Joins path segments using posix separators.
 * @param base the base absolute path
 * @param segments additional path segments to join
 * @returns the joined path as a branded NormalizedAbsolutePath
 */
export declare function joinPaths(base: NormalizedAbsolutePath, ...segments: string[]): NormalizedAbsolutePath;
/**
 * Type-safe basename that extracts the filename from a path.
 * @param filePath the path to extract the basename from
 * @returns the filename (last segment of the path)
 */
export declare function basenamePath(filePath: NormalizedPath | NormalizedAbsolutePath): string;
