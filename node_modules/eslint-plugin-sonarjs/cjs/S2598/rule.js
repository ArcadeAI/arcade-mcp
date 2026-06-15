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
// https://sonarsource.github.io/rspec/#/rspec/S2598/javascript
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
exports.getVariablePropertyFromAssignment = getVariablePropertyFromAssignment;
const location_js_1 = require("../helpers/location.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const module_js_1 = require("../helpers/module.js");
const ast_js_1 = require("../helpers/ast.js");
const meta = __importStar(require("./generated-meta.js"));
const FORMIDABLE_MODULE = 'formidable';
const KEEP_EXTENSIONS = 'keepExtensions';
const UPLOAD_DIR = 'uploadDir';
const MULTER_MODULE = 'multer';
const STORAGE_OPTION = 'storage';
const DESTINATION_OPTION = 'destination';
const formidableObjects = new Map();
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
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
                    report(context, value.uploadDirSet, value.keepExtensions, value.callExpression);
                }
            },
        };
    },
};
function checkCallExpression(context, callExpression) {
    const { callee } = callExpression;
    if (callee.type !== 'Identifier') {
        return;
    }
    const fqn = (0, module_js_1.getFullyQualifiedName)(context, callee);
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
}
function checkFormidable(context, callExpression) {
    if (callExpression.arguments.length === 0) {
        const formVariable = (0, ast_js_1.getLhsVariable)(context, callExpression);
        if (formVariable) {
            formidableObjects.set(formVariable, {
                uploadDirSet: false,
                keepExtensions: false,
                callExpression,
            });
        }
        return;
    }
    const options = (0, ast_js_1.getValueOfExpression)(context, callExpression.arguments[0], 'ObjectExpression');
    if (options) {
        report(context, !!(0, ast_js_1.getProperty)(options, UPLOAD_DIR, context), keepExtensionsValue((0, ast_js_1.getProperty)(options, KEEP_EXTENSIONS, context)?.value), callExpression);
    }
}
function checkMulter(context, callExpression) {
    if (callExpression.arguments.length === 0) {
        return;
    }
    const multerOptions = (0, ast_js_1.getValueOfExpression)(context, callExpression.arguments[0], 'ObjectExpression');
    if (!multerOptions) {
        return;
    }
    const storagePropertyValue = (0, ast_js_1.getProperty)(multerOptions, STORAGE_OPTION, context)?.value;
    if (storagePropertyValue) {
        const storageValue = (0, ast_js_1.getValueOfExpression)(context, storagePropertyValue, 'CallExpression');
        if (storageValue) {
            const diskStorageCallee = getDiskStorageCalleeIfUnsafeStorage(context, storageValue);
            if (diskStorageCallee) {
                report(context, false, false, callExpression, (0, location_js_1.toSecondaryLocation)(diskStorageCallee, 'no destination specified'));
            }
        }
    }
}
function getDiskStorageCalleeIfUnsafeStorage(context, storageCreation) {
    const { arguments: args, callee } = storageCreation;
    if (args.length > 0 && isMemberWithProperty(callee, 'diskStorage')) {
        const storageOptions = (0, ast_js_1.getValueOfExpression)(context, args[0], 'ObjectExpression');
        if (storageOptions && !(0, ast_js_1.getProperty)(storageOptions, DESTINATION_OPTION, context)) {
            return callee;
        }
    }
    return false;
}
function isMemberWithProperty(expr, property) {
    return (expr.type === 'MemberExpression' &&
        expr.property.type === 'Identifier' &&
        expr.property.name === property);
}
function keepExtensionsValue(extensionValue) {
    if (extensionValue?.type === 'Literal' && typeof extensionValue.value === 'boolean') {
        return extensionValue.value;
    }
    return false;
}
function visitAssignment(context, assignment) {
    const variableProperty = getVariablePropertyFromAssignment(context, assignment);
    if (!variableProperty) {
        return;
    }
    const { objectVariable, property } = variableProperty;
    const formOptions = formidableObjects.get(objectVariable);
    if (formOptions !== undefined) {
        if (property === UPLOAD_DIR) {
            formOptions.uploadDirSet = true;
        }
        if (property === KEEP_EXTENSIONS) {
            formOptions.keepExtensions = keepExtensionsValue(assignment.right);
        }
    }
}
/**
 * for `x.foo = 42` returns 'x' variable and 'foo' property string
 */
function getVariablePropertyFromAssignment(context, assignment) {
    if (assignment.left.type !== 'MemberExpression') {
        return undefined;
    }
    const memberExpr = assignment.left;
    if (memberExpr.object.type === 'Identifier' && memberExpr.property.type === 'Identifier') {
        const objectVariable = (0, ast_js_1.getVariableFromName)(context, memberExpr.object.name, memberExpr);
        if (objectVariable) {
            return { objectVariable, property: memberExpr.property.name };
        }
    }
    return undefined;
}
function report(context, uploadDirSet, keepExtensions, callExpression, secondaryLocation) {
    let message;
    if (keepExtensions && uploadDirSet) {
        message = 'Restrict the extension of uploaded files.';
    }
    else if (!keepExtensions && !uploadDirSet) {
        message = 'Restrict folder destination of uploaded files.';
    }
    else if (keepExtensions && !uploadDirSet) {
        message = 'Restrict the extension and folder destination of uploaded files.';
    }
    if (message) {
        (0, location_js_1.report)(context, {
            message,
            node: callExpression.callee,
        }, secondaryLocation ? [secondaryLocation] : []);
    }
}
