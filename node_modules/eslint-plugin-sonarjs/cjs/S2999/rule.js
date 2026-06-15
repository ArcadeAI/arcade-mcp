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
// https://sonarsource.github.io/rspec/#/rspec/S2999/javascript
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
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.rule = void 0;
const typescript_1 = __importDefault(require("typescript"));
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const type_js_1 = require("../helpers/type.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        const considerJSDoc = !!context.options[0]?.considerJSDoc;
        const services = context.sourceCode.parserServices;
        if (!(0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {};
        }
        return {
            'NewExpression[callee.type!="ThisExpression"]': (node) => {
                const { callee } = node;
                const type = (0, type_js_1.getTypeFromTreeNode)(callee, services);
                const signature = (0, type_js_1.getSignatureFromCallee)(node, services);
                if (!isInstantiable(type, signature, considerJSDoc) && !isAny(type)) {
                    const functionToken = context.sourceCode.getFirstToken(node, token => token.type === 'Keyword' && token.value === 'function');
                    const newToken = context.sourceCode.getFirstToken(node, token => token.type === 'Keyword' && token.value === 'new');
                    const text = isFunction(type) ? 'this function' : context.sourceCode.getText(callee);
                    const loc = callee.type === 'FunctionExpression' ? functionToken.loc : callee.loc;
                    (0, location_js_1.report)(context, {
                        message: `Replace ${text} with a constructor function.`,
                        loc,
                    }, [(0, location_js_1.toSecondaryLocation)(newToken)]);
                }
            },
        };
    },
};
function isInstantiable(type, signature, considerJSDoc) {
    return (isClass(type) ||
        isModule(type) ||
        isConstructor(type, signature, considerJSDoc) ||
        (type.isUnionOrIntersection() &&
            type.types.some(tp => isInstantiable(tp, signature, considerJSDoc))));
}
function isClass(type) {
    return (type.symbol &&
        ((type.symbol.flags & typescript_1.default.SymbolFlags.Class) !== 0 ||
            (type.symbol.flags & typescript_1.default.SymbolFlags.Type) !== 0));
}
function isModule(type) {
    return type.symbol && (type.symbol.flags & typescript_1.default.SymbolFlags.Module) !== 0;
}
function isFunction(type) {
    return type.symbol && (type.symbol.flags & typescript_1.default.SymbolFlags.Function) !== 0;
}
function isConstructor(type, signature, considerJSDoc) {
    return isFunction(type) && (!considerJSDoc || hasJSDocAnnotation(signature));
}
function hasJSDocAnnotation(signature) {
    return signature?.getJsDocTags().some(tag => ['constructor', 'class'].includes(tag.name));
}
function isAny(type) {
    return type.flags === typescript_1.default.TypeFlags.Any;
}
