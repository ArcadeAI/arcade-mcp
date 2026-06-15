"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.getElementType = void 0;
exports.isPresentationTable = isPresentationTable;
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
const jsx_ast_utils_x_1 = __importDefault(require("jsx-ast-utils-x"));
const { getProp, getLiteralPropValue, elementType } = jsx_ast_utils_x_1.default;
function isPresentationTable(context, node) {
    const DISALLOWED_VALUES = ['presentation', 'none'];
    const type = (0, exports.getElementType)(context)(node);
    if (type.toLowerCase() !== 'table') {
        return false;
    }
    const role = getProp(node.attributes, 'role');
    if (!role) {
        return false;
    }
    const roleValue = String(getLiteralPropValue(role));
    return DISALLOWED_VALUES.includes(roleValue?.toLowerCase());
}
const getElementType = (context) => {
    const { settings } = context;
    const jsxa11ySettings = settings['jsx-a11y'];
    const polymorphicPropName = jsxa11ySettings?.polymorphicPropName;
    const polymorphicAllowList = jsxa11ySettings?.polymorphicAllowList;
    const componentMap = jsxa11ySettings?.components;
    return (node) => {
        const prop = polymorphicPropName
            ? getProp(node.attributes, polymorphicPropName)
            : undefined;
        const polymorphicProp = prop ? getLiteralPropValue(prop) : undefined;
        let rawType = elementType(node);
        if (polymorphicProp &&
            (!polymorphicAllowList || polymorphicAllowList.includes(rawType))) {
            rawType = `${polymorphicProp}`;
        }
        if (!componentMap) {
            return rawType;
        }
        return componentMap.hasOwnProperty(rawType)
            ? componentMap[rawType]
            : rawType;
    };
};
exports.getElementType = getElementType;
