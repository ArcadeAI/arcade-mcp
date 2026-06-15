import ts from 'typescript';
import type { ParserServicesWithTypeInformation } from '@typescript-eslint/utils';
export declare function getFullyQualifiedNameTS(services: ParserServicesWithTypeInformation, rootNode: ts.Node): string | null;
