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
// https://sonarsource.github.io/rspec/#/rspec/S4323/javascript
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
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
const TYPE_THRESHOLD = 2;
const USAGE_THRESHOLD = 2;
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        let usage;
        return {
            Program: () => (usage = new Map()),
            'Program:exit': () => {
                for (const nodes of usage.values()) {
                    if (nodes.length > USAGE_THRESHOLD) {
                        const [node, ...rest] = nodes;
                        const kind = node.type === 'TSUnionType' ? 'union' : 'intersection';
                        const message = `Replace this ${kind} type with a type alias.`;
                        (0, location_js_1.report)(context, { message, loc: node.loc }, rest.map(node => (0, location_js_1.toSecondaryLocation)(node, 'Following occurrence.')));
                    }
                }
            },
            'TSUnionType, TSIntersectionType': (node) => {
                const ancestors = context.sourceCode.getAncestors(node);
                const declaration = ancestors.find(ancestor => ancestor.type === 'TSTypeAliasDeclaration');
                if (declaration) {
                    return;
                }
                const composite = node;
                if (composite.types.length <= TYPE_THRESHOLD) {
                    return;
                }
                if (isNullableType(composite)) {
                    return;
                }
                const text = composite.types
                    .map(typeNode => context.sourceCode.getText(typeNode))
                    .sort((a, b) => a.localeCompare(b))
                    .join('|');
                let occurrences = usage.get(text);
                if (occurrences) {
                    occurrences.push(composite);
                }
                else {
                    occurrences = [composite];
                    usage.set(text, occurrences);
                }
            },
        };
        function isNullableType(node) {
            return (node.type === 'TSUnionType' &&
                node.types.filter(type => type.type !== 'TSNullKeyword' && type.type !== 'TSUndefinedKeyword').length === 1);
        }
    },
};
