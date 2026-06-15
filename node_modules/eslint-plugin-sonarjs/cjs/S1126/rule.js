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
        messages: {
            replaceIfThenElseByReturn: 'Replace this if-then-else flow by a single return statement.',
            suggest: 'Replace with single return statement',
            suggestCast: 'Replace with single return statement using "!!" cast',
            suggestBoolean: 'Replace with single return statement without cast (condition should be boolean!)',
        },
        hasSuggestions: true,
    }),
    create(context) {
        return {
            IfStatement(node) {
                const parent = node.parent;
                if (
                // ignore `else if`
                parent.type !== 'IfStatement' &&
                    returnsBoolean(node.consequent) &&
                    alternateReturnsBoolean(node)) {
                    const suggestions = getSuggestion(node, parent);
                    context.report({
                        messageId: 'replaceIfThenElseByReturn',
                        node,
                        ...(suggestions.length > 0 ? { suggest: suggestions } : {}),
                    });
                }
            },
        };
        function getSuggestion(ifStmt, parent) {
            const replacementRange = getReplacementRange(ifStmt, parent);
            if (replacementRange === null || hasCommentsInRange(replacementRange)) {
                return [];
            }
            const getFix = (condition) => {
                return (fixer) => {
                    const singleReturn = `return ${condition};`;
                    return fixer.replaceTextRange(replacementRange, singleReturn);
                };
            };
            const shouldNegate = isReturningFalse(ifStmt.consequent);
            const shouldCast = !isBooleanExpression(ifStmt.test);
            const testText = context.sourceCode.getText(ifStmt.test);
            if (shouldNegate) {
                return [{ messageId: 'suggest', fix: getFix(`!(${testText})`) }];
            }
            else if (shouldCast) {
                return [
                    { messageId: 'suggestCast', fix: getFix(`!!(${testText})`) },
                    { messageId: 'suggestBoolean', fix: getFix(testText) },
                ];
            }
            else {
                return [{ messageId: 'suggest', fix: getFix(testText) }];
            }
        }
        function hasCommentsInRange(range) {
            return context.sourceCode.getAllComments().some(comment => {
                const commentRange = comment.range;
                return (commentRange !== undefined && commentRange[0] >= range[0] && commentRange[1] <= range[1]);
            });
        }
    },
};
function getReplacementRange(ifStmt, parent) {
    const ifStmtRange = ifStmt.range;
    if (ifStmtRange === undefined) {
        return null;
    }
    if (ifStmt.alternate || parent.type !== 'BlockStatement') {
        return ifStmtRange;
    }
    const ifStmtIndex = parent.body.indexOf(ifStmt);
    const returnStmt = parent.body[ifStmtIndex + 1];
    const returnStmtRange = returnStmt?.range;
    if (returnStmtRange === undefined) {
        return null;
    }
    return [ifStmtRange[0], returnStmtRange[1]];
}
function isBlockReturningBooleanLiteral(statement) {
    return (statement.type === 'BlockStatement' &&
        statement.body.length === 1 &&
        isSimpleReturnBooleanLiteral(statement.body[0]));
}
function isSimpleReturnBooleanLiteral(statement) {
    return (statement?.type === 'ReturnStatement' &&
        statement.argument?.type === 'Literal' &&
        typeof statement.argument.value === 'boolean');
}
function isReturningFalse(stmt) {
    const returnStmt = (stmt.type === 'BlockStatement' ? stmt.body[0] : stmt);
    return returnStmt.argument.value === false;
}
function isBooleanExpression(expr) {
    return ((expr.type === 'UnaryExpression' || expr.type === 'BinaryExpression') &&
        ['!', '==', '===', '!=', '!==', '<', '<=', '>', '>=', 'in', 'instanceof'].includes(expr.operator));
}
function returnsBoolean(statement) {
    return (statement !== undefined &&
        (isBlockReturningBooleanLiteral(statement) || isSimpleReturnBooleanLiteral(statement)));
}
function alternateReturnsBoolean(node) {
    if (node.alternate) {
        return returnsBoolean(node.alternate);
    }
    const { parent } = node;
    if (parent?.type === 'BlockStatement') {
        for (const [index, stmt] of parent.body.entries()) {
            if (stmt === node) {
                return isSimpleReturnBooleanLiteral(parent.body[index + 1]);
            }
            // We check if there are more ifStatements to look for validator patterns
            else if (stmt.type === 'IfStatement' &&
                returnsBoolean(stmt.consequent)) {
                return false;
            }
        }
    }
    return false;
}
