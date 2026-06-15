export default abstract class Detector {
    probability: number;
    constructor(probability: number);
    abstract scan(line: string): number;
    recognition(line: string): number;
}
