import type { Minimatch } from 'minimatch';
import { type File, type NormalizedAbsolutePath } from '../files.js';
import fs from 'node:fs';
import { ComputedCache } from '../cache.js';
export interface Filesystem {
    readdirSync: (typeof fs)['readdirSync'];
    readFileSync: (typeof fs)['readFileSync'];
    statSync: (typeof fs)['statSync'];
}
export declare const MinimatchCache: ComputedCache<Minimatch, ComputedCache<NormalizedAbsolutePath, File[], null>, Filesystem>;
