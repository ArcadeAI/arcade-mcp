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
// https://sonarsource.github.io/rspec/#/rspec/S6302/javascript
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
const result_js_1 = require("../helpers/result.js");
const iam_js_1 = require("../helpers/aws/iam.js");
const generate_meta_js_1 = require("../helpers/generate-meta.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
const MESSAGES = {
    message: 'Make sure granting all privileges is safe here.',
    secondary: 'Related effect',
};
exports.rule = (0, iam_js_1.AwsIamPolicyTemplate)(allPrivilegesStatementChecker, (0, generate_meta_js_1.generateMeta)(meta));
function allPrivilegesStatementChecker(expr, ctx, options) {
    const properties = (0, result_js_1.getResultOfExpression)(ctx, expr);
    const effect = (0, iam_js_1.getSensitiveEffect)(properties, ctx, options);
    const action = getSensitiveAction(properties, options);
    if (effect.isMissing && action) {
        (0, location_js_1.report)(ctx, {
            message: MESSAGES.message,
            node: action,
        });
    }
    else if (effect.isFound && action) {
        (0, location_js_1.report)(ctx, {
            message: MESSAGES.message,
            node: action,
        }, [(0, location_js_1.toSecondaryLocation)(effect.node, MESSAGES.secondary)]);
    }
}
function getSensitiveAction(properties, options) {
    return getActionLiterals(properties, options).find(iam_js_1.isAnyLiteral);
}
function getActionLiterals(properties, options) {
    return properties.getProperty(options.actions.property).asStringLiterals();
}
