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
// https://sonarsource.github.io/rspec/#/rspec/S1128/javascript
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
const vue_js_1 = require("../helpers/vue.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const quickfix_js_1 = require("../helpers/quickfix.js");
const meta = __importStar(require("./generated-meta.js"));
const EXCLUDED_IMPORTS = new Set(['React']);
const JSDOC_TAGS = [
    '@abstract',
    '@access',
    '@alias',
    '@arg',
    '@argument',
    '@async',
    '@augments',
    '@author',
    '@borrows',
    '@callback',
    '@class',
    '@classdesc',
    '@const',
    '@constant',
    '@constructor',
    '@constructs',
    '@copyright',
    '@default',
    '@defaultvalue',
    '@deprecated',
    '@desc',
    '@description',
    '@emits',
    '@enum',
    '@event',
    '@example',
    '@exception',
    '@exports',
    '@extends',
    '@external',
    '@file',
    '@fileoverview',
    '@fires',
    '@func',
    '@function',
    '@generator',
    '@global',
    '@hideconstructor',
    '@host',
    '@ignore',
    '@implements',
    '@inheritdoc',
    '@inner',
    '@instance',
    '@interface',
    '@kind',
    '@lends',
    '@license',
    '@link',
    '@linkcode',
    '@linkplain',
    '@listens',
    '@member',
    '@memberof',
    '@method',
    '@mixes',
    '@mixin',
    '@module',
    '@name',
    '@namespace',
    '@override',
    '@overview',
    '@package',
    '@param',
    '@private',
    '@prop',
    '@property',
    '@protected',
    '@public',
    '@readonly',
    '@requires',
    '@return',
    '@returns',
    '@see',
    '@since',
    '@static',
    '@summary',
    '@this',
    '@throws',
    '@todo',
    '@tutorial',
    '@type',
    '@typedef',
    '@var',
    '@variation',
    '@version',
    '@virtual',
    '@yield',
    '@yields',
];
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            removeUnusedImport: `Remove this unused import of '{{symbol}}'.`,
            suggestRemoveWholeStatement: `Remove this import statement`,
            suggestRemoveOneVariable: `Remove this variable import`,
        },
        hasSuggestions: true,
    }),
    create(context) {
        const isJsxPragmaSet = context.sourceCode
            .getAllComments()
            .some(comment => comment.value.includes('@jsx jsx'));
        const unusedImports = [];
        const tsTypeIdentifiers = new Set();
        const vueIdentifiers = new Set();
        const saveTypeIdentifier = (node) => tsTypeIdentifiers.add(node.name);
        function isImplicitJsx(variable) {
            return variable.name === 'jsx' && isJsxPragmaSet;
        }
        const ruleListener = {
            ImportDeclaration: (node) => {
                const variables = context.sourceCode.getDeclaredVariables(node);
                for (const variable of variables) {
                    if (!isExcluded(variable) && !isImplicitJsx(variable) && isUnused(variable)) {
                        unusedImports.push({
                            id: variable.identifiers[0],
                            importDecl: node,
                        });
                    }
                }
            },
            'TSTypeReference > Identifier, TSClassImplements > Identifier, TSInterfaceHeritage > Identifier': (node) => {
                saveTypeIdentifier(node);
            },
            "TSQualifiedName[left.type = 'Identifier']": (node) => {
                saveTypeIdentifier(node.left);
            },
            "TSInterfaceHeritage > MemberExpression[object.type = 'Identifier'], TSClassImplements > MemberExpression[object.type = 'Identifier']": (node) => {
                saveTypeIdentifier(node.object);
            },
            'Program:exit': () => {
                const jsxFactories = getJsxFactories(context);
                const jsxIdentifiers = getJsxIdentifiers(context);
                const jsDocComments = getJsDocComments(context);
                for (const unused of unusedImports.filter(({ id: unused }) => !jsxIdentifiers.includes(unused.name) &&
                    !tsTypeIdentifiers.has(unused.name) &&
                    !(vueIdentifiers.has(unused.name) && (0, vue_js_1.isInsideVueSetupScript)(unused, context)) &&
                    !jsxFactories.has(unused.name) &&
                    !jsDocComments.some(comment => comment.value.includes(unused.name)))) {
                    context.report({
                        messageId: 'removeUnusedImport',
                        data: {
                            symbol: unused.id.name,
                        },
                        node: unused.id,
                        suggest: [getSuggestion(context, unused)],
                    });
                }
            },
        };
        // @ts-ignore
        if (context.sourceCode.parserServices.defineTemplateBodyVisitor) {
            return context.sourceCode.parserServices.defineTemplateBodyVisitor({
                VElement: (node) => {
                    const { rawName } = node;
                    const name = rawName.split('.')[0];
                    vueIdentifiers.add(toCamelCase(name));
                    vueIdentifiers.add(toPascalCase(name));
                },
                VDirectiveKey: (node) => {
                    const { name: { name }, } = node;
                    const camelCased = toCamelCase(name);
                    const pascalCased = toPascalCase(name);
                    vueIdentifiers.add(camelCased);
                    vueIdentifiers.add(pascalCased);
                    vueIdentifiers.add(`v${camelCased}`);
                    vueIdentifiers.add(`v${pascalCased}`);
                },
                Identifier: (node) => {
                    vueIdentifiers.add(node.name);
                },
            }, ruleListener, { templateBodyTriggerSelector: 'Program' });
        }
        return ruleListener;
    },
};
// vue only capitalizes the char after '-'
function toCamelCase(str) {
    return str.replaceAll(/-\w/g, s => s[1].toUpperCase());
}
function toPascalCase(str) {
    const camelized = toCamelCase(str);
    return camelized[0].toUpperCase() + camelized.slice(1);
}
function getSuggestion(context, { id, importDecl }) {
    const variables = context.sourceCode.getDeclaredVariables(importDecl);
    if (variables.length === 1) {
        return {
            messageId: 'suggestRemoveWholeStatement',
            fix: fixer => {
                return (0, quickfix_js_1.removeNodeWithLeadingWhitespaces)(context, importDecl, fixer);
            },
        };
    }
    const specifiers = importDecl.specifiers;
    const unusedSpecifier = specifiers.find(specifier => specifier.local === id);
    const code = context.sourceCode;
    let range;
    switch (unusedSpecifier.type) {
        case 'ImportDefaultSpecifier': {
            const tokenAfter = code.getTokenAfter(id);
            // default import is always first
            range = [id.range[0], code.getTokenAfter(tokenAfter).range[0]];
            break;
        }
        case 'ImportNamespaceSpecifier':
            // namespace import is always second
            range = [code.getTokenBefore(unusedSpecifier).range[0], unusedSpecifier.range[1]];
            break;
        case 'ImportSpecifier': {
            const simpleSpecifiers = specifiers.filter(specifier => specifier.type === 'ImportSpecifier');
            const index = simpleSpecifiers.indexOf(unusedSpecifier);
            if (simpleSpecifiers.length === 1) {
                range = [specifiers[0].range[1], code.getTokenAfter(unusedSpecifier).range[1]];
            }
            else if (index === 0) {
                range = [simpleSpecifiers[0].range[0], simpleSpecifiers[1].range[0]];
            }
            else {
                range = [simpleSpecifiers[index - 1].range[1], simpleSpecifiers[index].range[1]];
            }
        }
    }
    return {
        messageId: 'suggestRemoveOneVariable',
        fix: fixer => {
            return fixer.removeRange(range);
        },
    };
}
function getJsxFactories(context) {
    const factories = new Set();
    const parserServices = context.sourceCode.parserServices;
    if ((0, parser_services_js_1.isRequiredParserServices)(parserServices)) {
        const compilerOptions = parserServices.program.getCompilerOptions();
        if (compilerOptions.jsxFactory) {
            factories.add(compilerOptions.jsxFactory);
        }
        if (compilerOptions.jsxFragmentFactory) {
            factories.add(compilerOptions.jsxFragmentFactory);
        }
    }
    return factories;
}
function getJsxIdentifiers(context) {
    return context.sourceCode.ast.tokens
        .filter(token => token.type === 'JSXIdentifier')
        .map(token => token.value);
}
function getJsDocComments(context) {
    return context.sourceCode
        .getAllComments()
        .filter(comment => comment.type === 'Block' && JSDOC_TAGS.some(tag => comment.value.includes(tag)));
}
function isExcluded(variable) {
    return EXCLUDED_IMPORTS.has(variable.name);
}
function isUnused(variable) {
    return variable.references.length === 0;
}
