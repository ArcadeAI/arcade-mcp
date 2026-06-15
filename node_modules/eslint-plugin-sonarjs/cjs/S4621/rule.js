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
// https://sonarsource.github.io/rspec/#/rspec/S4621/javascript
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
const location_js_1 = require("../helpers/location.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, { hasSuggestions: true }),
    create(context) {
        return {
            'TSUnionType, TSIntersectionType'(node) {
                const sourceCode = context.sourceCode;
                const compositeType = node;
                const groupedTypes = new Map();
                for (const typescriptType of compositeType.types) {
                    const nodeValue = sourceCode.getText(typescriptType);
                    const nodesWithGivenType = groupedTypes.get(nodeValue);
                    const nodeType = typescriptType;
                    if (nodesWithGivenType) {
                        nodesWithGivenType.push(nodeType);
                    }
                    else {
                        groupedTypes.set(nodeValue, [nodeType]);
                    }
                }
                for (const duplicates of groupedTypes.values()) {
                    if (duplicates.length > 1) {
                        const suggest = getSuggestions(compositeType, duplicates, context);
                        const primaryNode = duplicates.splice(1, 1)[0];
                        const secondaryLocations = duplicates.map((node, index) => (0, location_js_1.toSecondaryLocation)(node, index ? 'Another duplicate' : 'Original'));
                        (0, location_js_1.report)(context, {
                            message: `Remove this duplicated type or replace with another one.`,
                            loc: primaryNode.loc,
                            suggest,
                        }, secondaryLocations);
                    }
                }
            },
        };
    },
};
function getSuggestions(composite, duplicates, context) {
    const ranges = duplicates.slice(1).map(duplicate => {
        const idx = composite.types.indexOf(duplicate);
        return [
            getEnd(context, composite.types[idx - 1], composite),
            getEnd(context, duplicate, composite),
        ];
    });
    return [
        {
            desc: 'Remove duplicate types',
            fix: fixer => ranges.map(r => fixer.removeRange(r)),
        },
    ];
}
function getEnd(context, node, composite) {
    let end = node;
    while (true) {
        const nextToken = context.sourceCode.getTokenAfter(end);
        if (nextToken?.value === ')' && nextToken.range[1] <= composite.range[1]) {
            end = nextToken;
        }
        else {
            break;
        }
    }
    return end.range[1];
}
