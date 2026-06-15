"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.createRegExpRule = createRegExpRule;
const regexpp = __importStar(require("@eslint-community/regexpp"));
const ast_js_1 = require("./ast.js");
const extract_js_1 = require("./extract.js");
const location_js_1 = require("./location.js");
const location_js_2 = require("../location.js");
const parser_services_js_1 = require("../parser-services.js");
/**
 * Rule template to create regex rules.
 * @param handlers - the regexpp node handlers
 * @param meta - the (optional) rule metadata
 * @returns the resulting rule module
 */
function createRegExpRule(handlers, meta = {}) {
    return {
        meta,
        create(context) {
            const services = (0, parser_services_js_1.isRequiredParserServices)(context.sourceCode.parserServices)
                ? context.sourceCode.parserServices
                : null;
            function checkRegex(node, regExpAST) {
                if (!regExpAST) {
                    return;
                }
                const ctx = Object.create(context);
                ctx.node = node;
                ctx.reportRegExpNode = reportRegExpNode;
                regexpp.visitRegExpAST(regExpAST, handlers(ctx));
            }
            function reportRegExpNode(descriptor, secondaryLocations) {
                const { node, regexpNode, offset = [0, 0], ...rest } = descriptor;
                const loc = (0, location_js_1.getRegexpLocation)(node, regexpNode, context, offset);
                if (loc) {
                    if (secondaryLocations?.length) {
                        (0, location_js_2.report)(context, { ...rest, loc }, secondaryLocations);
                    }
                    else {
                        context.report({ ...rest, loc });
                    }
                }
            }
            function checkLiteral(literal) {
                checkRegex(literal, (0, extract_js_1.getParsedRegex)(literal, context));
            }
            function checkCallExpression(callExpr) {
                let parsedRegex = (0, extract_js_1.getParsedRegex)(callExpr, context);
                if (!parsedRegex && services && (0, ast_js_1.isStringRegexMethodCall)(callExpr, services)) {
                    const [implicitRegex] = callExpr.arguments;
                    parsedRegex = (0, extract_js_1.getParsedRegex)(implicitRegex, context);
                }
                checkRegex(callExpr.arguments[0], parsedRegex);
            }
            return {
                'Literal[regex]': checkLiteral,
                NewExpression: checkCallExpression,
                CallExpression: checkCallExpression,
            };
        },
    };
}
