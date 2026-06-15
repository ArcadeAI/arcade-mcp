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
// https://sonarsource.github.io/rspec/#/rspec/S3800/javascript
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
const type_js_1 = require("../helpers/type.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const location_js_1 = require("../helpers/location.js");
const ancestor_js_1 = require("../helpers/ancestor.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const collection_js_1 = require("../helpers/collection.js");
const meta = __importStar(require("./generated-meta.js"));
class FunctionScope {
    constructor() {
        this.returnStatements = [];
    }
    getReturnStatements() {
        return this.returnStatements.slice();
    }
    addReturnStatement(node) {
        this.returnStatements.push(node);
    }
}
const isASanitationFunction = (signature) => {
    const { types } = signature.getReturnType();
    return types.length === 2 && types.some(type_js_1.isBooleanTrueType) && types.some(type_js_1.isStringType);
};
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        let scopes = [];
        const services = context.sourceCode.parserServices;
        if (!(0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {};
        }
        const checker = services.program.getTypeChecker();
        function onFunctionExit(node) {
            const returnStatements = scopes.pop().getReturnStatements();
            if (returnStatements.some(retStmt => retStmt.argument?.type === 'ThisExpression')) {
                return;
            }
            const signature = checker.getSignatureFromDeclaration(services.esTreeNodeToTSNodeMap.get(node));
            if (signature && hasMultipleReturnTypes(signature, checker)) {
                if (isASanitationFunction(signature)) {
                    return;
                }
                // Exclude null-like and any-typed returns; any-typed returns come from external/unknown
                // functions whose signature is unavailable and cannot contribute to type inconsistency.
                const stmts = returnStatements.filter(retStmt => {
                    const type = (0, type_js_1.getTypeFromTreeNode)(retStmt.argument, services);
                    return !isNullLike(type) && !(0, type_js_1.isAny)(type);
                });
                const stmtsTypes = stmts.map(retStmt => (0, type_js_1.getTypeFromTreeNode)(retStmt.argument, services));
                const stmtCategories = stmtsTypes.map(t => prettyPrint(t, checker));
                if (stmtCategories.filter((val, i, arr) => distinct(val, i, arr)).length <= 1) {
                    return;
                }
                (0, location_js_1.report)(context, {
                    message: 'Refactor this function to always return the same type.',
                    loc: (0, location_js_1.getMainFunctionTokenLocation)(node, (0, ancestor_js_1.getParent)(context, node), context),
                }, stmts.map((stmt, i) => (0, location_js_1.toSecondaryLocation)(stmt, `Returns ${prettyPrint(stmtsTypes[i], checker)}`)));
            }
        }
        return {
            ReturnStatement: (node) => {
                const retStmt = node;
                if (scopes.length > 0 && retStmt.argument) {
                    (0, collection_js_1.last)(scopes).addReturnStatement(retStmt);
                }
            },
            ':function': () => {
                scopes.push(new FunctionScope());
            },
            ':function:exit': onFunctionExit,
            'Program:exit': () => {
                scopes = [];
            },
        };
    },
};
function hasMultipleReturnTypes(signature, checker) {
    const returnType = checker.getBaseTypeOfLiteralType(checker.getReturnTypeOfSignature(signature));
    return isMixingTypes(returnType, checker) && !hasReturnTypeJSDoc(signature);
}
function isMixingTypes(type, checker) {
    return (type.isUnion() &&
        type.types
            .filter(tp => !isNullLike(tp))
            .map(tp => prettyPrint(tp, checker))
            .filter((val, i, arr) => distinct(val, i, arr)).length > 1);
}
function hasReturnTypeJSDoc(signature) {
    return signature.getJsDocTags().some(tag => ['return', 'returns'].includes(tag.name));
}
function isObjectLikeType(type) {
    return !!(type.getFlags() & typescript_1.default.TypeFlags.Object);
}
function distinct(value, index, self) {
    return self.indexOf(value) === index;
}
function prettyPrint(type, checker) {
    if (type.isUnionOrIntersection()) {
        const delimiter = type.isUnion() ? ' | ' : ' & ';
        return type.types
            .map(tp => prettyPrint(tp, checker))
            .filter((val, i, arr) => distinct(val, i, arr))
            .join(delimiter);
    }
    const typeNode = checker.typeToTypeNode(type, undefined, undefined);
    if (typeNode !== undefined) {
        if (typescript_1.default.isFunctionTypeNode(typeNode)) {
            return 'function';
        }
        if (typescript_1.default.isArrayTypeNode(typeNode) || isTypedArray(type, checker)) {
            return 'array';
        }
    }
    if (isObjectLikeType(type)) {
        return 'object';
    }
    return checker.typeToString(checker.getBaseTypeOfLiteralType(type));
}
function isTypedArray(type, checker) {
    const typeAsString = checker.typeToString(type);
    // Since TS 5.7 typed arrays include the type of the elements in the string, eg. Float32Array<any>
    return /.*Array(?:<[^>]*>)?$/.test(typeAsString);
}
function isNullLike(type) {
    return ((type.flags & typescript_1.default.TypeFlags.Null) !== 0 ||
        (type.flags & typescript_1.default.TypeFlags.Void) !== 0 ||
        (type.flags & typescript_1.default.TypeFlags.Undefined) !== 0);
}
