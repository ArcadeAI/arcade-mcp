import Detector from '../Detector.js';
export default class KeywordsDetector extends Detector {
    keywords: string[];
    constructor(probability: number, ...keywords: string[]);
    scan(line: string): number;
}
