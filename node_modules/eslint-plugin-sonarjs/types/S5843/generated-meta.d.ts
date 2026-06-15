export * from './meta.js';
export declare const meta: {
    type: "suggestion";
    docs: {
        description: string;
        recommended: boolean;
        url: string;
        requiresTypeChecking: true;
    };
    fixable: undefined;
    deprecated: false;
    defaultOptions: {
        threshold: number;
    }[];
};
export declare const sonarKey = "S5843";
export declare const scope = "Main";
export declare const languages: ('js' | 'ts')[];
export declare const requiredDependency: never[];
