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
// https://sonarsource.github.io/rspec/#/rspec/S6443/javascript
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
const module_js_1 = require("../helpers/module.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
const declarationSelector = [
    ':matches(',
    [
        'VariableDeclarator[init.callee.name="useState"]',
        'VariableDeclarator[init.callee.object.type="Identifier"][init.callee.property.name="useState"]',
    ].join(','),
    ')',
    '[id.type="ArrayPattern"]',
    '[id.elements.length=2]',
    '[id.elements.0.type="Identifier"]',
    '[id.elements.1.type="Identifier"]',
].join('');
const callSelector = [
    'CallExpression[callee.type="Identifier"]',
    '[arguments.length=1]',
    '[arguments.0.type="Identifier"]',
].join('');
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            uselessSetState: 'Change the argument of this setter to not use its matching state variable',
        },
    }),
    create(context) {
        const referencesBySetterName = {};
        return {
            [declarationSelector](node) {
                if (isReactCall(context, node.init)) {
                    const { elements } = node.id;
                    const setter = elements[1].name;
                    referencesBySetterName[setter] = {
                        setter: (0, ast_js_1.getVariableFromName)(context, setter, node),
                        value: (0, ast_js_1.getVariableFromName)(context, elements[0].name, node),
                    };
                }
            },
            [callSelector](node) {
                const setter = (0, ast_js_1.getVariableFromName)(context, node.callee.name, node);
                const value = (0, ast_js_1.getVariableFromName)(context, node.arguments[0].name, node);
                const key = setter?.name;
                if (setter &&
                    value &&
                    referencesBySetterName.hasOwnProperty(key) &&
                    referencesBySetterName[key].setter === setter &&
                    referencesBySetterName[key].value === value) {
                    context.report({
                        messageId: 'uselessSetState',
                        node,
                    });
                }
            },
        };
    },
};
function isReactCall(context, callExpr) {
    const fqn = (0, module_js_1.getFullyQualifiedName)(context, callExpr);
    if (fqn) {
        const [module] = fqn.split('.');
        return module === 'react';
    }
    return false;
}
