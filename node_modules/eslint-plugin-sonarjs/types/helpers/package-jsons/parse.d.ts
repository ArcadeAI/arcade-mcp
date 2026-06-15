import { Minimatch } from 'minimatch';
import type { PackageJson } from 'type-fest';
type MinimatchDependency = {
    name: Minimatch;
    version?: string;
};
type NamedDependency = {
    name: string;
    version?: string;
};
type Dependency = MinimatchDependency | NamedDependency;
export declare function getDependenciesFromPackageJson(content: PackageJson): Set<Dependency>;
export {};
