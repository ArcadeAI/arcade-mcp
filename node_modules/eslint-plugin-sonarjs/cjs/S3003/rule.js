"use strict";
/*
 * SonarQube JavaScript Plugin
 * Copyright (C) SonarSource Sàrl
 * mailto:info AT sonarsource DOT com
 *
 * You can redistribute and/or modify this program under the terms of
 * the Sonar Source-Available License Version 1, as published by SonarSource Sàrl.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the Sonar Source-Available License for more details.
 *
 * You should have received a copy of the Sonar Source-Available License
 * along with this program; if not, see https://sonarsource.com/license/ssal/
 */
// https://sonarsource.github.io/rspec/#/rspec/S3003/javascript
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
exports.rule = void 0;
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const type_js_1 = require("../helpers/type.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const services = context.sourceCode.parserServices;
        if (!(0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {};
        }
        return {
            BinaryExpression: (node) => {
                const { operator, left, right } = node;
                if (['<', '<=', '>', '>='].includes(operator) &&
                    (0, type_js_1.isString)(left, services) &&
                    (0, type_js_1.isString)(right, services) &&
                    !isLiteralException(left) &&
                    !isLiteralException(right) &&
                    !isWithinSortCallback(context, node)) {
                    (0, location_js_1.report)(context, {
                        message: `Convert operands of this use of "${operator}" to number type.`,
                        loc: context.sourceCode
                            .getTokensBetween(left, right)
                            .find(token => token.type === 'Punctuator' && token.value === operator).loc,
                    }, [left, right].map(node => (0, location_js_1.toSecondaryLocation)(node)));
                }
            },
        };
    },
};
function isLiteralException(node) {
    return node.type === 'Literal' && node.raw.length === 3;
}
function isWithinSortCallback(context, node) {
    const ancestors = context.sourceCode.getAncestors(node).reverse();
    const maybeCallback = ancestors.find(node => node.type === 'ArrowFunctionExpression' || node.type === 'FunctionExpression');
    if (maybeCallback) {
        const callback = maybeCallback;
        const parent = callback.parent;
        if (parent?.type === 'CallExpression') {
            const { callee, arguments: args } = parent;
            let funcName;
            if (callee.type === 'Identifier') {
                funcName = callee.name;
            }
            else if (callee.type === 'MemberExpression' && callee.property.type === 'Identifier') {
                funcName = callee.property.name;
            }
            return funcName?.match(/sort/i) && args.includes(callback);
        }
    }
    return false;
}
