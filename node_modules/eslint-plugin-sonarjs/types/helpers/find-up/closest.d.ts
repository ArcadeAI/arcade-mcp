import { type File, type NormalizedAbsolutePath } from '../files.js';
import { ComputedCache } from '../cache.js';
import { type Filesystem } from './find-minimatch.js';
export declare const closestPatternCache: ComputedCache<string, ComputedCache<NormalizedAbsolutePath, ComputedCache<NormalizedAbsolutePath, File | undefined, null>, null>, Filesystem>;
