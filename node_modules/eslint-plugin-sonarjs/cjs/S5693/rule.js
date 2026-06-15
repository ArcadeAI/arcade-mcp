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
// https://sonarsource.github.io/rspec/#/rspec/S5693/javascript
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
const rule_js_1 = require("../S2598/rule.js");
const bytes_1 = require("bytes");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const module_js_1 = require("../helpers/module.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
const FORMIDABLE_MODULE = 'formidable';
const MAX_FILE_SIZE = 'maxFileSize';
const FORMIDABLE_DEFAULT_SIZE = 200 * 1024 * 1024;
const MULTER_MODULE = 'multer';
const LIMITS_OPTION = 'limits';
const FILE_SIZE_OPTION = 'fileSize';
const BODY_PARSER_MODULE = 'body-parser';
const BODY_PARSER_DEFAULT_SIZE = (0, bytes_1.parse)('100kb');
const formidableObjects = new Map();
const DEFAULT_OPTIONS = {
    fileUploadSizeLimit: 8_000_000,
    standardSizeLimit: 2_000_000,
};
const messages = {
    safeLimit: 'Make sure the content length limit is safe here.',
};
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, { messages }),
    create(context) {
        return {
            NewExpression(node) {
                checkCallExpression(context, node);
            },
            CallExpression(node) {
                checkCallExpression(context, node);
            },
            AssignmentExpression(node) {
                visitAssignment(context, node);
            },
            Program() {
                formidableObjects.clear();
            },
            'Program:exit'() {
                for (const value of formidableObjects.values()) {
                    report(context, value.nodeToReport, value.maxFileSize);
                }
            },
        };
    },
};
function checkCallExpression(context, callExpression) {
    const { callee } = callExpression;
    let identifierFromModule;
    if (callee.type === 'MemberExpression' && callee.object.type === 'Identifier') {
        identifierFromModule = callee.object;
    }
    else if (callee.type === 'Identifier') {
        identifierFromModule = callee;
    }
    else {
        return;
    }
    const fqn = (0, module_js_1.getFullyQualifiedName)(context, identifierFromModule);
    if (!fqn) {
        return;
    }
    const [moduleName] = fqn.split('.');
    if (moduleName === FORMIDABLE_MODULE) {
        checkFormidable(context, callExpression);
    }
    if (moduleName === MULTER_MODULE) {
        checkMulter(context, callExpression);
    }
    if (moduleName === BODY_PARSER_MODULE) {
        checkBodyParser(context, callExpression);
    }
}
function checkFormidable(context, callExpression) {
    if (callExpression.arguments.length === 0) {
        // options will be set later through member assignment
        const formVariable = (0, ast_js_1.getLhsVariable)(context, callExpression);
        if (formVariable) {
            formidableObjects.set(formVariable, {
                maxFileSize: FORMIDABLE_DEFAULT_SIZE,
                nodeToReport: callExpression,
            });
        }
        return;
    }
    const options = (0, ast_js_1.getValueOfExpression)(context, callExpression.arguments[0], 'ObjectExpression');
    if (options) {
        const property = (0, ast_js_1.getProperty)(options, MAX_FILE_SIZE, context);
        checkSize(context, callExpression, property, FORMIDABLE_DEFAULT_SIZE);
    }
}
function checkMulter(context, callExpression) {
    if (callExpression.callee.type === 'MemberExpression') {
        return;
    }
    if (callExpression.arguments.length === 0) {
        report(context, callExpression.callee);
        return;
    }
    const multerOptions = (0, ast_js_1.getValueOfExpression)(context, callExpression.arguments[0], 'ObjectExpression');
    if (!multerOptions) {
        return;
    }
    const limitsPropertyValue = (0, ast_js_1.getProperty)(multerOptions, LIMITS_OPTION, context)?.value;
    if (limitsPropertyValue?.type === 'ObjectExpression') {
        const fileSizeProperty = (0, ast_js_1.getProperty)(limitsPropertyValue, FILE_SIZE_OPTION, context);
        checkSize(context, callExpression, fileSizeProperty);
    }
    if (!limitsPropertyValue) {
        report(context, callExpression.callee);
    }
}
function checkBodyParser(context, callExpression) {
    if (callExpression.arguments.length === 0) {
        checkSize(context, callExpression, undefined, BODY_PARSER_DEFAULT_SIZE, true);
        return;
    }
    const options = (0, ast_js_1.getValueOfExpression)(context, callExpression.arguments[0], 'ObjectExpression');
    if (!options) {
        return;
    }
    const limitsProperty = (0, ast_js_1.getProperty)(options, LIMITS_OPTION, context);
    checkSize(context, callExpression, limitsProperty, BODY_PARSER_DEFAULT_SIZE, true);
}
function checkSize(context, callExpr, property, defaultLimit, useStandardSizeLimit = false) {
    if (property) {
        const maxFileSizeValue = getSizeValue(context, property.value);
        if (maxFileSizeValue) {
            report(context, property, maxFileSizeValue, useStandardSizeLimit);
        }
    }
    else {
        report(context, callExpr, defaultLimit, useStandardSizeLimit);
    }
}
function visitAssignment(context, assignment) {
    const variableProperty = (0, rule_js_1.getVariablePropertyFromAssignment)(context, assignment);
    if (!variableProperty) {
        return;
    }
    const { objectVariable, property } = variableProperty;
    const formOptions = formidableObjects.get(objectVariable);
    if (formOptions && property === MAX_FILE_SIZE) {
        const rhsValue = getSizeValue(context, assignment.right);
        if (rhsValue) {
            formOptions.maxFileSize = rhsValue;
            formOptions.nodeToReport = assignment;
        }
        else {
            formidableObjects.delete(objectVariable);
        }
    }
}
function getSizeValue(context, node) {
    const literal = (0, ast_js_1.getValueOfExpression)(context, node, 'Literal');
    if (literal) {
        if (typeof literal.value === 'number') {
            return literal.value;
        }
        else if (typeof literal.value === 'string') {
            return (0, bytes_1.parse)(literal.value);
        }
    }
    return null;
}
function report(context, nodeToReport, size, useStandardSizeLimit = false) {
    const { fileUploadSizeLimit, standardSizeLimit } = {
        ...DEFAULT_OPTIONS,
        ...context.options[0],
    };
    const limitToCompare = useStandardSizeLimit ? standardSizeLimit : fileUploadSizeLimit;
    if (!size || size > limitToCompare) {
        context.report({
            messageId: 'safeLimit',
            node: nodeToReport,
        });
    }
}
