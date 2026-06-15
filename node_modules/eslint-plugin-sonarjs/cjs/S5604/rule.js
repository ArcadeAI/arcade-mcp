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
// https://sonarsource.github.io/rspec/#/rspec/S5604/javascript
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
const GEOLOCATION = 'geolocation';
const CAMERA = 'camera';
const MICROPHONE = 'microphone';
const NOTIFICATIONS = 'notifications';
const PERSISTENT_STORAGE = 'persistent-storage';
const supportedPermissions = new Set([
    GEOLOCATION,
    CAMERA,
    MICROPHONE,
    NOTIFICATIONS,
    PERSISTENT_STORAGE,
]);
const DEFAULT_PERMISSIONS = [GEOLOCATION];
const messages = {
    checkPermission: 'Make sure the use of the {{feature}} is necessary.',
};
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta, { messages }),
    create(context) {
        const permissions = context.options[0]?.permissions ?? DEFAULT_PERMISSIONS;
        return {
            'CallExpression[callee.type="MemberExpression"]'(node) {
                const call = node;
                const callee = call.callee;
                if (isNavigatorMemberExpression(callee, 'permissions', 'query') &&
                    call.arguments.length > 0) {
                    checkPermissions(context, call, permissions);
                    return;
                }
                if (permissions.includes(GEOLOCATION) &&
                    isNavigatorMemberExpression(callee, GEOLOCATION, 'watchPosition', 'getCurrentPosition')) {
                    context.report({
                        messageId: 'checkPermission',
                        data: {
                            feature: GEOLOCATION,
                        },
                        node: callee,
                    });
                    return;
                }
                if (isNavigatorMemberExpression(callee, 'mediaDevices', 'getUserMedia') &&
                    call.arguments.length > 0) {
                    const firstArg = (0, ast_js_1.getValueOfExpression)(context, call.arguments[0], 'ObjectExpression');
                    checkForCameraAndMicrophonePermissions(context, permissions, callee, firstArg);
                    return;
                }
                if (permissions.includes(NOTIFICATIONS) &&
                    (0, ast_js_1.isMemberExpression)(callee, 'Notification', 'requestPermission')) {
                    context.report({
                        messageId: 'checkPermission',
                        data: {
                            feature: NOTIFICATIONS,
                        },
                        node: callee,
                    });
                    return;
                }
                if (permissions.includes(PERSISTENT_STORAGE) &&
                    (0, ast_js_1.isMemberExpression)(callee.object, 'navigator', 'storage')) {
                    context.report({
                        messageId: 'checkPermission',
                        data: {
                            feature: PERSISTENT_STORAGE,
                        },
                        node: callee,
                    });
                }
            },
            NewExpression(node) {
                const { callee } = node;
                if (permissions.includes(NOTIFICATIONS) && (0, ast_js_1.isIdentifier)(callee, 'Notification')) {
                    context.report({
                        messageId: 'checkPermission',
                        data: {
                            feature: NOTIFICATIONS,
                        },
                        node: callee,
                    });
                }
            },
        };
    },
};
function checkForCameraAndMicrophonePermissions(context, permissions, callee, firstArg) {
    if (!firstArg) {
        return;
    }
    const shouldCheckAudio = permissions.includes('microphone');
    const shouldCheckVideo = permissions.includes(CAMERA);
    if (!shouldCheckAudio && !shouldCheckVideo) {
        return;
    }
    const perms = [];
    for (const prop of firstArg.properties) {
        if (prop.type === 'Property') {
            const { value, key } = prop;
            if ((0, ast_js_1.isIdentifier)(key, 'audio') && shouldCheckAudio && isOtherThanFalse(context, value)) {
                perms.push('microphone');
            }
            else if ((0, ast_js_1.isIdentifier)(key, 'video') &&
                shouldCheckVideo &&
                isOtherThanFalse(context, value)) {
                perms.push(CAMERA);
            }
        }
    }
    if (perms.length > 0) {
        context.report({
            messageId: 'checkPermission',
            data: {
                feature: perms.join(' and '),
            },
            node: callee,
        });
    }
}
function isOtherThanFalse(context, value) {
    const exprValue = (0, ast_js_1.getValueOfExpression)(context, value, 'Literal');
    if (exprValue?.value === false) {
        return false;
    }
    return true;
}
function checkPermissions(context, call, permissions) {
    const firstArg = (0, ast_js_1.getValueOfExpression)(context, call.arguments[0], 'ObjectExpression');
    if (firstArg?.type === 'ObjectExpression') {
        const nameProp = firstArg.properties.find(prop => hasNamePropertyWithPermission(prop, context, permissions));
        if (nameProp) {
            const { value } = nameProp.value;
            context.report({
                messageId: 'checkPermission',
                data: {
                    feature: String(value),
                },
                node: nameProp,
            });
        }
    }
}
function isNavigatorMemberExpression({ object, property }, firstProperty, ...secondProperty) {
    return ((0, ast_js_1.isMemberExpression)(object, 'navigator', firstProperty) &&
        (0, ast_js_1.isIdentifier)(property, ...secondProperty));
}
function hasNamePropertyWithPermission(prop, context, permissions) {
    if (prop.type === 'Property' && (0, ast_js_1.isIdentifier)(prop.key, 'name')) {
        const value = (0, ast_js_1.getValueOfExpression)(context, prop.value, 'Literal');
        return (value &&
            typeof value.value === 'string' &&
            supportedPermissions.has(value.value) &&
            permissions.includes(value.value));
    }
    return false;
}
