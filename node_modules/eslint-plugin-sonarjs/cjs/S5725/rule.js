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
// https://sonarsource.github.io/rspec/#/rspec/S5725/javascript
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
const type_js_1 = require("../helpers/type.js");
const ast_js_1 = require("../helpers/ast.js");
const parser_services_js_1 = require("../helpers/parser-services.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, {
        messages: {
            safeResource: 'Make sure not using resource integrity feature is safe here.',
        },
    }),
    create(context) {
        const services = context.sourceCode.parserServices;
        if (!(0, parser_services_js_1.isRequiredParserServices)(services)) {
            return {};
        }
        return {
            'VariableDeclarator[init.type="CallExpression"]': (node) => {
                const variableDeclarator = node;
                const callExpression = variableDeclarator.init;
                const left = variableDeclarator.id;
                const { callee } = callExpression;
                if (left.type !== 'Identifier') {
                    return;
                }
                if (callee.type !== 'MemberExpression') {
                    return;
                }
                const typeName = (0, type_js_1.getTypeAsString)(left, services);
                if (!(0, ast_js_1.isIdentifier)(callee.object, 'document') ||
                    !(0, ast_js_1.isIdentifier)(callee.property, 'createElement') ||
                    typeName !== 'HTMLScriptElement') {
                    return;
                }
                const scope = context.sourceCode.getScope(node);
                const assignedVariable = scope.variables.find(v => v.name === left.name);
                if (!assignedVariable) {
                    return;
                }
                if (shouldReport(assignedVariable)) {
                    context.report({
                        node: variableDeclarator,
                        messageId: 'safeResource',
                    });
                }
            },
        };
    },
};
function isIntegrityAssignment(memberExpression) {
    if (memberExpression.type !== 'MemberExpression') {
        return false;
    }
    return (memberExpression.property.type === 'Identifier' &&
        memberExpression.property.name === 'integrity');
}
function isSrcAssignment(memberExpression) {
    if (memberExpression.type !== 'MemberExpression') {
        return false;
    }
    if (memberExpression.property.type !== 'Identifier' || memberExpression.property.name !== 'src') {
        return false;
    }
    const assignmentExpression = memberExpression.parent;
    return assignmentExpression?.type === 'AssignmentExpression';
}
function isUnsafeSrcAssignment(memberExpression) {
    if (!isSrcAssignment(memberExpression)) {
        return false;
    }
    const right = memberExpression.parent.right;
    if (right.type !== 'Literal') {
        return false;
    }
    return !!right.raw && (!!right.raw.match('^"http') || !!right.raw.match('^"//'));
}
function shouldReport(assignedVariable) {
    let nbSrcAssignment = 0;
    let hasUnsafeSrcAssignment = false;
    let hasIntegrityAssignment = false;
    for (const ref of assignedVariable.references) {
        const parentNode = ref.identifier.parent;
        if (!parentNode) {
            continue;
        }
        nbSrcAssignment += isSrcAssignment(parentNode) ? 1 : 0;
        hasUnsafeSrcAssignment = hasUnsafeSrcAssignment || isUnsafeSrcAssignment(parentNode);
        hasIntegrityAssignment = hasIntegrityAssignment || isIntegrityAssignment(parentNode);
    }
    return nbSrcAssignment === 1 && hasUnsafeSrcAssignment && !hasIntegrityAssignment;
}
