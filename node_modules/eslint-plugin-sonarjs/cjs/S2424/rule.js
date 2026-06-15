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
// https://sonarsource.github.io/rspec/#/rspec/S2424/javascript
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
const globals_1 = __importDefault(require("globals"));
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            removeOverride: 'Remove this override of "{{overridden}}".',
        },
    }),
    create(context) {
        const overridden = new Set();
        function checkVariable(variable) {
            if (isBuiltIn(variable)) {
                for (const def of variable.defs) {
                    overridden.add(def.name);
                }
                for (const ref of variable.references.filter(ref => ref.isWrite())) {
                    overridden.add(ref.identifier);
                }
            }
        }
        function checkScope(scope) {
            for (const variable of scope.variables) {
                checkVariable(variable);
            }
            for (const childScope of scope.childScopes) {
                checkScope(childScope);
            }
        }
        function isTSEnumMemberId(node) {
            const id = node;
            return id.parent?.type === 'TSEnumMember';
        }
        return {
            Program: (node) => {
                checkScope(context.sourceCode.getScope(node));
            },
            'Program:exit': () => {
                for (const node of overridden) {
                    if (!isTSEnumMemberId(node)) {
                        context.report({
                            messageId: 'removeOverride',
                            data: {
                                overridden: node.name,
                            },
                            node,
                        });
                    }
                }
                overridden.clear();
            },
        };
    },
};
function isBuiltIn(variable) {
    return variable.name in globals_1.default.builtin;
}
