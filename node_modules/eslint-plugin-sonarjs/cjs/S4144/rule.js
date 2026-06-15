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
// https://sonarsource.github.io/rspec/#/rspec/S4144
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
const equivalence_js_1 = require("../helpers/equivalence.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const location_js_1 = require("../helpers/location.js");
const collection_js_1 = require("../helpers/collection.js");
const meta = __importStar(require("./generated-meta.js"));
const DEFAULT_MIN_LINES = 3;
const message = 'Update this function so that its implementation is not identical to the one on line {{line}}.';
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            identicalFunctions: message,
        },
    }),
    create(context) {
        const functions = [];
        const minLines = context.options[0] ?? DEFAULT_MIN_LINES;
        return {
            FunctionDeclaration(node) {
                visitFunction(node);
            },
            'VariableDeclarator > FunctionExpression, MethodDefinition > FunctionExpression': (node) => {
                visitFunction(node);
            },
            'VariableDeclarator > ArrowFunctionExpression, MethodDefinition > ArrowFunctionExpression': (node) => {
                visitFunction(node);
            },
            'Program:exit'() {
                processFunctions();
            },
        };
        function visitFunction(node) {
            if (isBigEnough(node.body)) {
                functions.push({ function: node, parent: node.parent });
            }
        }
        function processFunctions() {
            for (let i = 1; i < functions.length; i++) {
                const duplicatingFunction = functions[i].function;
                for (let j = 0; j < i; j++) {
                    const originalFunction = functions[j].function;
                    if ((0, equivalence_js_1.areEquivalent)(duplicatingFunction.body, originalFunction.body, context.sourceCode) &&
                        originalFunction.loc) {
                        const loc = (0, location_js_1.getMainFunctionTokenLocation)(duplicatingFunction, functions[i].parent, context);
                        const originalFunctionLoc = (0, location_js_1.getMainFunctionTokenLocation)(originalFunction, functions[j].parent, context);
                        const secondaryLocations = [
                            (0, location_js_1.toSecondaryLocation)({ loc: originalFunctionLoc }, 'Original implementation'),
                        ];
                        (0, location_js_1.report)(context, {
                            message,
                            data: {
                                line: originalFunction.loc.start.line,
                            },
                            loc,
                        }, secondaryLocations);
                        break;
                    }
                }
            }
        }
        function isBigEnough(node) {
            const tokens = context.sourceCode.getTokens(node);
            if (tokens.length > 0 && tokens[0].value === '{') {
                tokens.shift();
            }
            if (tokens.length > 0 && (0, collection_js_1.last)(tokens).value === '}') {
                tokens.pop();
            }
            if (tokens.length > 0) {
                const firstLine = tokens[0].loc.start.line;
                const lastLine = (0, collection_js_1.last)(tokens).loc.end.line;
                return lastLine - firstLine + 1 >= minLines;
            }
            return false;
        }
    },
};
