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
// https://sonarsource.github.io/rspec/#/rspec/S6079/javascript
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
const reaching_definitions_js_1 = require("../helpers/reaching-definitions.js");
const mocha_js_1 = require("../helpers/mocha.js");
const location_js_1 = require("../helpers/location.js");
const meta = __importStar(require("./generated-meta.js"));
exports.rule = {
    meta: (0, generate_meta_js_1.generateMeta)(meta),
    create(context) {
        let currentDoneVariable;
        let doneCall;
        let doneSegment;
        let currentSegment;
        let currentCase;
        const segmentFirstStatement = new Map();
        function checkForTestCase(node) {
            const testCase = (0, mocha_js_1.extractTestCase)(node);
            if (!testCase) {
                return;
            }
            currentCase = testCase;
            currentDoneVariable = undefined;
            if (testCase.callback.params.length === 0) {
                return;
            }
            const [done] = testCase.callback.params;
            if (done.type !== 'Identifier') {
                return;
            }
            const callbackScope = context.sourceCode
                .getScope(node)
                .childScopes.find(scope => scope.block === testCase.callback);
            if (!callbackScope) {
                return;
            }
            currentDoneVariable = (0, reaching_definitions_js_1.getVariableFromIdentifier)(done, callbackScope);
        }
        function checkForDoneCall(node) {
            const { callee } = node;
            if (currentDoneVariable?.references.some(ref => ref.identifier === callee)) {
                doneCall = node;
                doneSegment = currentSegment;
            }
        }
        function report(statementAfterDone) {
            (0, location_js_1.report)(context, {
                node: statementAfterDone,
                message: `Move this code before the call to "done".`,
            }, [(0, location_js_1.toSecondaryLocation)(doneCall)]);
            doneSegment = undefined;
            doneCall = undefined;
            currentDoneVariable = undefined;
        }
        return {
            CallExpression: (node) => {
                checkForTestCase(node);
                checkForDoneCall(node);
            },
            ExpressionStatement: (node) => {
                if (currentSegment && currentSegment === doneSegment) {
                    report(node);
                }
                if (currentSegment && !segmentFirstStatement.has(currentSegment)) {
                    segmentFirstStatement.set(currentSegment, node);
                }
            },
            onCodePathSegmentStart(segment) {
                currentSegment = segment;
            },
            onCodePathEnd(_codePath, node) {
                currentSegment = undefined;
                if (currentCase?.callback === node && doneSegment) {
                    // we report an issue if one of 'doneSegment.nextSegments' is not empty
                    const statementAfterDone = doneSegment.nextSegments
                        .map(segment => segmentFirstStatement.get(segment))
                        .find(stmt => !!stmt);
                    if (statementAfterDone) {
                        report(statementAfterDone);
                    }
                }
            },
        };
    },
};
