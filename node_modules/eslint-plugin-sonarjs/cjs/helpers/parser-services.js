"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.isRequiredParserServices = isRequiredParserServices;
function isRequiredParserServices(services) {
    // see https://github.com/typescript-eslint/typescript-eslint/issues/7124
    return !!services?.program;
}
