import type { Rule } from 'eslint';
import type { RulesMeta } from '@eslint/core';
import type { JSONSchema4 } from '@typescript-eslint/utils/json-schema';
import type { ESLintConfiguration } from './configs.js';
export type SonarMeta = {
    meta: Rule.RuleMetaData & {
        docs?: {
            requiresTypeChecking?: boolean;
        };
    };
    sonarKey: string;
    eslintId: string;
    scope: 'All' | 'Main' | 'Tests';
    languages: ('ts' | 'js')[];
    blacklistedExtensions?: string[];
    schema?: JSONSchema4;
    hasSecondaries?: boolean;
    fields?: ESLintConfiguration;
    implementation: 'original' | 'external' | 'decorated';
    externalPlugin?: string;
    externalRules?: {
        externalPlugin: string;
        externalRule: string;
    }[];
    quickFixMessage?: string;
};
export declare function generateMeta(sonarMeta: SonarMeta, ruleMeta?: RulesMeta): RulesMeta;
