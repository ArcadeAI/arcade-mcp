"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CodeRecognizer = void 0;
class CodeRecognizer {
    constructor(threshold, language) {
        this.language = language;
        this.threshold = threshold;
    }
    recognition(line) {
        let probability = 0;
        for (const pattern of this.language.getDetectors()) {
            probability = 1 - (1 - probability) * (1 - pattern.recognition(line));
        }
        return probability;
    }
    extractCodeLines(lines) {
        return lines.filter(line => this.recognition(line) >= this.threshold);
    }
    isLineOfCode(line) {
        return this.recognition(line) - this.threshold > 0;
    }
}
exports.CodeRecognizer = CodeRecognizer;
