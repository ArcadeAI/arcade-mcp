export * from './meta.js';
export declare const meta: {
    type: "suggestion";
    docs: {
        description: string;
        recommended: boolean;
        url: string;
        requiresTypeChecking: false;
    };
    fixable: undefined;
    deprecated: false;
    defaultOptions: {
        threshold: number;
        ignoreStrings: string;
    }[];
};
export declare const sonarKey = "S1192";
export declare const scope = "Main";
export declare const languages: ('js' | 'ts')[];
export declare const requiredDependency: never[];
