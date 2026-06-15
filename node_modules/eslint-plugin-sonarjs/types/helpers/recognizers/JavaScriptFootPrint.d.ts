import type Detector from './Detector.js';
import type LanguageFootprint from './LanguageFootprint.js';
export declare class JavaScriptFootPrint implements LanguageFootprint {
    detectors: Set<Detector>;
    constructor();
    getDetectors(): Set<Detector>;
}
