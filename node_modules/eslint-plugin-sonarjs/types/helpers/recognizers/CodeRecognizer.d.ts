import type LanguageFootprint from './LanguageFootprint.js';
export declare class CodeRecognizer {
    language: LanguageFootprint;
    threshold: number;
    constructor(threshold: number, language: LanguageFootprint);
    recognition(line: string): number;
    extractCodeLines(lines: string[]): string[];
    isLineOfCode(line: string): boolean;
}
