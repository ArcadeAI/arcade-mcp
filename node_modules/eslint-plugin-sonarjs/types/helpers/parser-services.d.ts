import type { ParserServices, ParserServicesWithTypeInformation } from '@typescript-eslint/utils';
export type RequiredParserServices = ParserServicesWithTypeInformation;
export declare function isRequiredParserServices(services: ParserServices | undefined): services is RequiredParserServices;
