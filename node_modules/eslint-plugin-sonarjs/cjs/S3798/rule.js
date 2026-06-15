"use strict";
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
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            defineLocally: 'Define this declaration in a local scope or bind explicitly the property to the global object.',
        },
    }),
    create(context) {
        return {
            Program(node) {
                const scope = context.sourceCode.getScope(node);
                // As we parse every file with "module" source type, we find user defined global variables in the module scope
                const moduleScope = findModuleScope(context);
                for (const variable of moduleScope?.variables ?? []) {
                    processVariable(context, scope, variable);
                }
            },
        };
    },
};
function processVariable(context, scope, variable) {
    if (scope.variables.some(global => global.name === variable.name)) {
        // Avoid reporting on redefinitions of actual global variables
        return;
    }
    for (const def of variable.defs) {
        const defNode = def.node;
        if (def.type === 'FunctionName' ||
            (def.type === 'Variable' && def.parent?.kind === 'var' && !isRequire(def.node.init))) {
            context.report({
                node: defNode,
                messageId: 'defineLocally',
            });
            return;
        }
    }
}
function findModuleScope(context) {
    return context.sourceCode.scopeManager.scopes.find(s => s.type === 'module');
}
function isRequire(node) {
    return (node?.type === 'CallExpression' &&
        node.arguments.length === 1 &&
        (0, ast_js_1.isIdentifier)(node.callee, 'require'));
}
