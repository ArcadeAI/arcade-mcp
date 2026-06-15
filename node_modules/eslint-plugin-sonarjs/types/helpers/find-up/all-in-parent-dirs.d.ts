import type { Filesystem } from './find-minimatch.js';
import { type File, type NormalizedAbsolutePath } from '../files.js';
import { ComputedCache } from '../cache.js';
export declare const patternInParentsCache: ComputedCache<string, ComputedCache<NormalizedAbsolutePath, ComputedCache<NormalizedAbsolutePath, File[], null>, null>, Filesystem>;
