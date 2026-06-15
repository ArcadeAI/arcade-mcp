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
// https://sonarsource.github.io/rspec/#/rspec/S2392/javascript
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
const collection_js_1 = require("../helpers/collection.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
function isForLoopNode(node) {
    return (node?.type === 'ForStatement' ||
        node?.type === 'ForInStatement' ||
        node?.type === 'ForOfStatement');
}
function getOtherLoopRanges(variable, varDeclaration) {
    const declRange = varDeclaration.range;
    const ranges = [];
    for (const def of variable.defs) {
        if (varDeclaration.declarations.includes(def.node)) {
            continue;
        }
        const loopNode = def.node.parent?.parent;
        const loopRange = loopNode?.range;
        if (isForLoopNode(loopNode) && loopRange) {
            // Exclude enclosing loops: only collect disjoint sibling loops
            if (declRange && loopRange[0] <= declRange[0] && loopRange[1] >= declRange[1]) {
                continue;
            }
            ranges.push(loopRange);
        }
    }
    return ranges;
}
function isCoveredByOtherLoops(referencesOutside, otherLoopRanges) {
    if (otherLoopRanges.length === 0) {
        return false;
    }
    return referencesOutside.every(ref => {
        const range = ref.range;
        return range !== undefined && otherLoopRanges.some(([s, e]) => range[0] >= s && range[1] <= e);
    });
}
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        let scopeRanges = [];
        let reported = [];
        function enterScope(node) {
            scopeRanges.push(node.range);
        }
        function exitScope() {
            scopeRanges.pop();
        }
        return {
            Program(node) {
                scopeRanges = [node.range];
                reported = [];
            },
            BlockStatement: enterScope,
            'BlockStatement:exit': exitScope,
            ForStatement: enterScope,
            'ForStatement:exit': exitScope,
            ForInStatement: enterScope,
            'ForInStatement:exit': exitScope,
            ForOfStatement: enterScope,
            'ForOfStatement:exit': exitScope,
            SwitchStatement: enterScope,
            'SwitchStatement:exit': exitScope,
            VariableDeclaration: (node) => {
                const varDeclaration = node;
                if (varDeclaration.kind !== 'var') {
                    return;
                }
                const scopeRange = (0, collection_js_1.last)(scopeRanges);
                function isOutsideOfScope(reference) {
                    const idRange = reference.range;
                    return idRange[0] < scopeRange[0] || idRange[1] > scopeRange[1];
                }
                for (const variable of context.sourceCode.getDeclaredVariables(node)) {
                    const referencesOutside = variable.references
                        .map(ref => ref.identifier)
                        .filter(isOutsideOfScope);
                    if (referencesOutside.length === 0) {
                        continue;
                    }
                    const varDeclParent = varDeclaration
                        .parent;
                    if (isForLoopNode(varDeclParent)) {
                        const otherLoopRanges = getOtherLoopRanges(variable, varDeclaration);
                        if (isCoveredByOtherLoops(referencesOutside, otherLoopRanges)) {
                            continue;
                        }
                    }
                    const definition = variable.defs.find(def => varDeclaration.declarations.includes(def.node));
                    if (definition && !reported.includes(definition.name)) {
                        (0, location_js_1.report)(context, {
                            node: definition.name,
                            message: `Consider moving declaration of '${variable.name}' ` +
                                `as it is referenced outside current binding context.`,
                        }, referencesOutside.map(node => (0, location_js_1.toSecondaryLocation)(node, 'Outside reference.')));
                        for (const defId of variable.defs.map(def => def.name)) {
                            reported.push(defId);
                        }
                    }
                }
            },
        };
    },
};
