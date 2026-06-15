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
// https://sonarsource.github.io/rspec/#/rspec/S4721/javascript
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
const EXEC_FUNCTIONS = new Set(['exec', 'execSync']);
const SPAWN_EXEC_FILE_FUNCTIONS = new Set(['spawn', 'spawnSync', 'execFile', 'execFileSync']);
const CHILD_PROCESS_MODULE = 'child_process';
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            safeOSCommand: 'Make sure that executing this OS command is safe here.',
        },
    }),
    create(context) {
        return {
            CallExpression: (node) => checkOSCommand(context, node),
        };
    },
};
function checkOSCommand(context, call) {
    const { callee, arguments: args } = call;
    const fqn = (0, module_js_1.getFullyQualifiedName)(context, call);
    if (!fqn) {
        return;
    }
    const fqnParts = fqn.split('.');
    const module = fqnParts[0];
    // JS-638: Use the last part of the FQN as the method (the actual method being called).
    const method = fqnParts.at(-1);
    if (method && module === CHILD_PROCESS_MODULE && isQuestionable(method, args)) {
        context.report({
            node: callee,
            messageId: 'safeOSCommand',
        });
    }
}
function isQuestionable(method, [command, ...otherArguments]) {
    // if command is hardcoded => no issue
    if (!command || (0, ast_js_1.isLiteral)(command) || (0, ast_js_1.isStaticTemplateLiteral)(command)) {
        return false;
    }
    // for `spawn` and `execFile`, `shell` option must be set to `true`
    if (SPAWN_EXEC_FILE_FUNCTIONS.has(method)) {
        return containsShellOption(otherArguments);
    }
    return EXEC_FUNCTIONS.has(method);
}
function containsShellOption(otherArguments) {
    return otherArguments.some(arg => arg.type === 'ObjectExpression' &&
        arg.properties
            .filter(v => v.type === 'Property')
            .some(({ key, value }) => (0, ast_js_1.isIdentifier)(key, 'shell') && value.type === 'Literal' && value.value === true));
}
