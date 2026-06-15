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
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        hasSuggestions: true,
    }),
    create(context) {
        function checkNewExpression(node) {
            const newExpression = node;
            if (newExpression.callee.type === 'Identifier' && newExpression.callee.name === 'Array') {
                let message = 'Use either a literal or "Array.from()" instead of the "Array" constructor.';
                let suggest = [
                    {
                        desc: 'Replace with a literal',
                        fix: replaceWithLiteralFix(newExpression, context),
                    },
                ];
                if (newExpression.arguments.length === 1 &&
                    newExpression.arguments[0].type === 'Literal' &&
                    typeof newExpression.arguments[0].value === 'number') {
                    message = 'Use "Array.from()" instead of the "Array" constructor.';
                }
                if (newExpression.arguments.length === 1) {
                    suggest = [
                        {
                            desc: 'Replace with "Array.from()"',
                            fix: replaceWithArrayFromFix(newExpression, context),
                        },
                    ];
                }
                context.report({ node, message, suggest });
            }
        }
        return {
            NewExpression: checkNewExpression,
        };
    },
};
function replaceWithLiteralFix(newExpression, context) {
    const argText = newExpression.arguments
        .map((arg) => context.sourceCode.getText(arg))
        .join(', ');
    return fixer => fixer.replaceText(newExpression, `[${argText}]`);
}
function replaceWithArrayFromFix(newExpression, context) {
    const argText = context.sourceCode.getText(newExpression.arguments[0]);
    return fixer => fixer.replaceText(newExpression, `Array.from({length: ${argText}})`);
}
