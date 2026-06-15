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
// https://sonarsource.github.io/rspec/#/rspec/S6299/javascript
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
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            safeVueBypassing: 'Make sure bypassing Vue built-in sanitization is safe here.',
        },
    }),
    create(context) {
        const services = context.sourceCode.parserServices;
        const ruleListener = {
            ["JSXAttribute[name.name='domPropsInnerHTML']," +
                "Property[key.name='domProps'] > ObjectExpression.value > Property[key.name='innerHTML']"](node) {
                context.report({ node, messageId: 'safeVueBypassing' });
            },
            [`${attrsHref('createElement')},${attrsHref('h')}`](node) {
                context.report({ node, messageId: 'safeVueBypassing' });
            },
        };
        // @ts-ignore
        if (services.defineTemplateBodyVisitor) {
            // analyze <template> in .vue file
            const templateBodyVisitor = context.sourceCode.parserServices.defineTemplateBodyVisitor({
                ["VAttribute[directive=true][key.name.name='html']," +
                    "VAttribute[directive=true][key.argument.name='href']"](node) {
                    context.report({
                        loc: node.loc,
                        messageId: 'safeVueBypassing',
                    });
                },
            });
            Object.assign(ruleListener, templateBodyVisitor);
        }
        return ruleListener;
    },
};
function attrsHref(calleeName) {
    // select call expression with given name where second argument is object expression like { attrs: { href: 'bla' } }
    return `CallExpression[callee.name='${calleeName}'] ObjectExpression.arguments:nth-child(2) > Property[key.name='attrs'] > ObjectExpression.value > Property[key.name='href']`;
}
