import Detector from '../Detector.js';
export default class EndWithDetector extends Detector {
    endOfLines: string[];
    constructor(probability: number, ...endOfLines: string[]);
    scan(line: string): number;
}
