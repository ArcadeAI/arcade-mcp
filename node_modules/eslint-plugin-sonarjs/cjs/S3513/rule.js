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
// https://sonarsource.github.io/rspec/#/rspec/S3513/javascript
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
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
const MESSAGE = "Use the rest syntax to declare this function's arguments.";
const SECONDARY_MESSAGE = 'Replace this reference to "arguments".';
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        return {
            // Ignore root scope containing global variables
            'Program:exit': (node) => {
                for (const child of context.sourceCode.getScope(node).childScopes) {
                    checkArgumentsUsageInScopeRecursively(context, child);
                }
            },
        };
    },
};
function checkArgumentsUsageInScopeRecursively(context, scope) {
    for (const variable of scope.variables.filter(variable => variable.name === 'arguments')) {
        checkArgumentsVariableWithoutDefinition(context, variable);
    }
    for (const child of scope.childScopes) {
        checkArgumentsUsageInScopeRecursively(context, child);
    }
}
function checkArgumentsVariableWithoutDefinition(context, variable) {
    // if variable is a parameter, variable.defs contains one ParameterDefinition with a type: 'Parameter'
    // if variable is a local variable, variable.defs contains one Definition with a type: 'Variable'
    // but if variable is the function arguments, variable.defs is just empty without other hint
    const isLocalVariableOrParameter = variable.defs.length > 0;
    const references = variable.references.filter(ref => !isFollowedByLengthProperty(ref));
    if (!isLocalVariableOrParameter && references.length > 0) {
        const firstReference = references[0];
        const secondaryLocations = references.slice(1).map(ref => ref.identifier);
        (0, location_js_1.report)(context, {
            node: firstReference.identifier,
            message: MESSAGE,
        }, secondaryLocations.map(node => (0, location_js_1.toSecondaryLocation)(node, SECONDARY_MESSAGE)));
    }
}
function isFollowedByLengthProperty(reference) {
    const parent = reference.identifier.parent;
    return (!!parent &&
        parent.type === 'MemberExpression' &&
        parent.property.type === 'Identifier' &&
        parent.property.name === 'length');
}
