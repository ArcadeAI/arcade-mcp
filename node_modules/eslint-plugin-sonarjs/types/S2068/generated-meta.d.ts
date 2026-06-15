export * from './meta.js';
export declare const meta: {
    type: "problem";
    docs: {
        description: string;
        recommended: boolean;
        url: string;
        requiresTypeChecking: false;
    };
    fixable: undefined;
    deprecated: false;
    defaultOptions: {
        passwordWords: string[];
    }[];
};
export declare const sonarKey = "S2068";
export declare const scope = "Main";
export declare const languages: ('js' | 'ts')[];
export declare const requiredDependency: never[];
