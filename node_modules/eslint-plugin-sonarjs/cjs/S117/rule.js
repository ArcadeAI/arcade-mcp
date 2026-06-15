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
// https://sonarsource.github.io/rspec/#/rspec/S117/javascript
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
const meta = __importStar(require("./generated-meta.js"));
const CAMEL_CASED = '^[_$A-Za-z][$A-Za-z0-9]*$';
const UPPER_CASED = '^[_$A-Z][_$A-Z0-9]+$';
const DEFAULT_FORMAT = `${CAMEL_CASED}|${UPPER_CASED}`;
const messages = {
    renameSymbol: `Rename this {{symbolType}} "{{symbol}}" to match the regular expression {{format}}.`,
};
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, { messages }),
    create(context) {
        return {
            VariableDeclaration: (node) => checkVariable(node, context),
            'FunctionDeclaration, FunctionExpression, ArrowFunctionExpression, TSDeclareFunction, TSMethodSignature, TSConstructSignatureDeclaration, TSEmptyBodyFunctionExpression': (node) => checkFunction(node, context),
            PropertyDefinition: (node) => checkProperty(node, context),
            CatchClause: (node) => checkCatch(node, context),
        };
    },
};
function checkVariable(decl, context) {
    if (decl.declare) {
        return;
    }
    for (const declaration of decl.declarations) {
        for (const id of (0, ast_js_1.resolveIdentifiers)(declaration.id)) {
            raiseOnInvalidIdentifier(id, 'local variable', context);
        }
    }
}
function checkFunction(func, context) {
    if (func.declare) {
        return;
    }
    for (const param of func.params) {
        for (const id of (0, ast_js_1.resolveIdentifiers)(param)) {
            raiseOnInvalidIdentifier(id, 'parameter', context);
        }
    }
}
function checkProperty(prop, context) {
    if (prop.key.type === 'Identifier') {
        raiseOnInvalidIdentifier(prop.key, 'property', context);
    }
}
function checkCatch(catchh, context) {
    if (catchh.param) {
        for (const id of (0, ast_js_1.resolveIdentifiers)(catchh.param)) {
            raiseOnInvalidIdentifier(id, 'parameter', context);
        }
    }
}
function raiseOnInvalidIdentifier(id, idType, context) {
    const format = context.options[0]?.format ?? DEFAULT_FORMAT;
    const { name } = id;
    if (!name.match(format)) {
        context.report({
            messageId: 'renameSymbol',
            data: {
                symbol: name,
                symbolType: idType,
                format,
            },
            node: id,
        });
    }
}
