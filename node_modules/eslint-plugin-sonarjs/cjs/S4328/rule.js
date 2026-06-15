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
// https://sonarsource.github.io/rspec/#/rspec/S4328/javascript
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
const builtin_modules_1 = __importDefault(require("builtin-modules"));
const typescript_1 = __importDefault(require("typescript"));
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const meta = __importStar(require("./generated-meta.js"));
const dependencies_js_1 = require("../helpers/package-jsons/dependencies.js");
const messages = {
    removeOrAddDependency: 'Either remove this import or add it as a dependency.',
};
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, { messages }),
    create(context) {
        // we need to find all the npm manifests from the directory of the analyzed file to the context working directory
        const dependencies = (0, dependencies_js_1.getDependenciesSanitizePaths)(context);
        const whitelist = context.options[0]?.whitelist || [];
        const program = context.sourceCode.parserServices?.program;
        let options, host;
        if (program) {
            options = program?.getCompilerOptions();
            host = typescript_1.default.createCompilerHost(options);
        }
        return {
            CallExpression: (node) => {
                const call = node;
                if (call.callee.type === 'Identifier' &&
                    call.callee.name === 'require' &&
                    call.arguments.length === 1) {
                    const [argument] = call.arguments;
                    if (argument.type === 'Literal') {
                        const requireToken = call.callee;
                        raiseOnImplicitImport(argument, requireToken.loc, dependencies, context.filename, host, options, whitelist, context);
                    }
                }
            },
            ImportDeclaration: (node) => {
                const module = node.source;
                const importToken = context.sourceCode.getFirstToken(node);
                raiseOnImplicitImport(module, importToken.loc, dependencies, context.filename, host, options, whitelist, context);
            },
        };
    },
};
function raiseOnImplicitImport(module, loc, dependencies, filename, host, options, whitelist, context) {
    const moduleValue = module.value;
    if (typeof moduleValue !== 'string') {
        return;
    }
    // Strip query parameters and hash fragments from module name
    // Bundlers like Vite use these for transformations (e.g., '?react' for SVG-to-React)
    const moduleName = moduleValue.split('?')[0].split('#')[0];
    if (typescript_1.default.isExternalModuleNameRelative(moduleName)) {
        return;
    }
    if (['node:', 'data:', 'file:'].some(prefix => moduleName.startsWith(prefix))) {
        return;
    }
    const packageName = getPackageName(moduleName);
    if (whitelist.includes(packageName)) {
        return;
    }
    if (builtin_modules_1.default.includes(packageName)) {
        return;
    }
    for (const dependency of dependencies) {
        if (typeof dependency === 'string') {
            if (dependency === packageName) {
                return;
            }
        }
        else if (dependency.match(moduleName)) {
            //dependencies are globs for workspaces
            return;
        }
    }
    if (host && options) {
        // check if Typescript can resolve path aliases and 'baseDir'-based import
        const resolved = typescript_1.default.resolveModuleName(moduleName, filename, options, host);
        if (resolved?.resolvedModule && !resolved.resolvedModule.isExternalLibraryImport) {
            return;
        }
    }
    context.report({
        messageId: 'removeOrAddDependency',
        loc,
    });
}
function getPackageName(name) {
    /*
      - scoped `@namespace/foo/bar` -> package `@namespace/foo`
      - scope `foo/bar` -> package `foo`
    */
    const parts = name.split('/');
    if (name.startsWith('@')) {
        return `${parts[0]}/${parts[1]}`;
    }
    else {
        return parts[0];
    }
}
