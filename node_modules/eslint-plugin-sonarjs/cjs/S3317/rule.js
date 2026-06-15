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
// https://sonarsource.github.io/rspec/#/rspec/S3317/javascript
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
const node_path_1 = __importDefault(require("node:path"));
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            renameFile: 'Rename this file to "{{exported}}"',
        },
    }),
    create(context) {
        let isOnlyExport = true;
        let nameOfExported = undefined;
        return {
            ExportDefaultDeclaration: (node) => {
                const declaration = node.declaration;
                if (declaration.type === 'Identifier') {
                    const variable = (0, ast_js_1.getVariableFromName)(context, declaration.name, node);
                    if (variable?.defs.length === 1) {
                        const def = variable.defs[0];
                        if (def.type === 'ClassName' || def.type === 'FunctionName' || isConst(def)) {
                            nameOfExported = declaration.name;
                        }
                    }
                }
                else if ((declaration.type === 'ClassDeclaration' || declaration.type === 'FunctionDeclaration') &&
                    declaration.id) {
                    nameOfExported = declaration.id.name;
                }
            },
            'ExportAllDeclaration, ExportNamedDeclaration': () => {
                isOnlyExport = false;
            },
            'Program:exit': () => {
                if (isOnlyExport && nameOfExported) {
                    const fileName = node_path_1.default.parse(context.filename).name;
                    if ('index' !== fileName &&
                        !sameName(nameOfExported, fileName) &&
                        !sameName(nameOfExported, sliceOffPostfix(fileName))) {
                        context.report({
                            messageId: 'renameFile',
                            data: {
                                exported: nameOfExported,
                            },
                            loc: { line: 0, column: 0 },
                        });
                    }
                }
            },
        };
    },
};
function sameName(nameOfExported, fileName) {
    const normalizedFileName = fileName.replaceAll('_', '').replaceAll('-', '').replaceAll('.', '');
    const normalizedNameOfExported = nameOfExported.replaceAll('_', '').replaceAll('-', '');
    return normalizedNameOfExported.toLowerCase() === normalizedFileName.toLowerCase();
}
function isConst(def) {
    return def.type === 'Variable' && def.parent?.kind === 'const';
}
function sliceOffPostfix(fileName) {
    return fileName.slice(0, fileName.lastIndexOf('.'));
}
