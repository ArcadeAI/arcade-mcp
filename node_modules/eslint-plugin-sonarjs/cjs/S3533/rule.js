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
// https://sonarsource.github.io/rspec/#/rspec/S3533/javascript
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
const ast_js_1 = require("../helpers/ast.js");
const type_js_1 = require("../helpers/type.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const collection_js_1 = require("../helpers/collection.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            standardImport: 'Use a standard "import" statement instead of "{{adhocImport}}".',
        },
    }),
    create(context) {
        const services = context.sourceCode.parserServices;
        return {
            'CallExpression[callee.type="Identifier"]': (node) => {
                if (context.sourceCode.getScope(node).type !== 'module' &&
                    context.sourceCode.getScope(node).type !== 'global') {
                    return;
                }
                const callExpression = node;
                const identifier = callExpression.callee;
                if (isAmdImport(callExpression, identifier, services) ||
                    isCommonJsImport(callExpression, identifier, services)) {
                    context.report({
                        node: identifier,
                        messageId: 'standardImport',
                        data: {
                            adhocImport: identifier.name,
                        },
                    });
                }
            },
        };
    },
};
function isString(node, services) {
    return (0, parser_services_js_1.isRequiredParserServices)(services) ? (0, type_js_1.isString)(node, services) : (0, ast_js_1.isStringLiteral)(node);
}
function isCommonJsImport(callExpression, identifier, services) {
    return (callExpression.arguments.length === 1 &&
        isString(callExpression.arguments[0], services) &&
        identifier.name === 'require');
}
function isAmdImport(callExpression, identifier, services) {
    if (identifier.name !== 'require' && identifier.name !== 'define') {
        return false;
    }
    if (callExpression.arguments.length !== 2 && callExpression.arguments.length !== 3) {
        return false;
    }
    return (0, parser_services_js_1.isRequiredParserServices)(services) && (0, type_js_1.isFunction)((0, collection_js_1.last)(callExpression.arguments), services);
}
