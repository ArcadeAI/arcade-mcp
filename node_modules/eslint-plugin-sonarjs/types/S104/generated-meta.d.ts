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
        maximum: number;
    }[];
};
export declare const sonarKey = "S104";
export declare const scope = "Main";
export declare const languages: ('js' | 'ts')[];
export declare const requiredDependency: never[];
