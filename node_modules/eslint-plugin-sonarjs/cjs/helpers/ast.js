"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.functionLike = exports.FUNCTION_NODES = void 0;
exports.isFunctionExpression = isFunctionExpression;
exports.isFunctionDeclaration = isFunctionDeclaration;
exports.isArrowFunctionExpression = isArrowFunctionExpression;
exports.isIdentifier = isIdentifier;
exports.getProgramStatements = getProgramStatements;
exports.isIfStatement = isIfStatement;
exports.isMemberWithProperty = isMemberWithProperty;
exports.isThrowStatement = isThrowStatement;
exports.isMemberExpression = isMemberExpression;
exports.isLogicalExpression = isLogicalExpression;
exports.isBinaryPlus = isBinaryPlus;
exports.isArrayExpression = isArrayExpression;
exports.isRequireModule = isRequireModule;
exports.isMethodInvocation = isMethodInvocation;
exports.isFunctionInvocation = isFunctionInvocation;
exports.isFunctionCall = isFunctionCall;
exports.isMethodCall = isMethodCall;
exports.isCallingMethod = isCallingMethod;
exports.isModuleExports = isModuleExports;
exports.isFunctionNode = isFunctionNode;
exports.isLiteral = isLiteral;
exports.isNullLiteral = isNullLiteral;
exports.isFalseLiteral = isFalseLiteral;
exports.isUndefined = isUndefined;
exports.isElementWrite = isElementWrite;
exports.isReferenceTo = isReferenceTo;
exports.getUniqueWriteUsage = getUniqueWriteUsage;
exports.getUniqueWriteReference = getUniqueWriteReference;
exports.getUniqueWriteUsageOrNode = getUniqueWriteUsageOrNode;
exports.getValueOfExpression = getValueOfExpression;
exports.getLhsVariable = getLhsVariable;
exports.getVariableFromScope = getVariableFromScope;
exports.getVariableFromName = getVariableFromName;
exports.flattenArgs = flattenArgs;
exports.resolveIdentifiers = resolveIdentifiers;
exports.getPropertyWithValue = getPropertyWithValue;
exports.getProperty = getProperty;
exports.resolveFromFunctionReference = resolveFromFunctionReference;
exports.resolveFunction = resolveFunction;
exports.checkSensitiveCall = checkSensitiveCall;
exports.isStringLiteral = isStringLiteral;
exports.isBooleanLiteral = isBooleanLiteral;
exports.isNumberLiteral = isNumberLiteral;
exports.isRegexLiteral = isRegexLiteral;
exports.isDotNotation = isDotNotation;
exports.isIndexNotation = isIndexNotation;
exports.isObjectDestructuring = isObjectDestructuring;
exports.isStaticTemplateLiteral = isStaticTemplateLiteral;
exports.isSimpleRawString = isSimpleRawString;
exports.getSimpleRawStringValue = getSimpleRawStringValue;
exports.isThisExpression = isThisExpression;
exports.isProperty = isProperty;
exports.isUnresolved = isUnresolved;
exports.hasParent = hasParent;
exports.hasTypePredicateReturn = hasTypePredicateReturn;
const ancestor_js_1 = require("./ancestor.js");
const collection_js_1 = require("./collection.js");
const module_js_1 = require("./module.js");
const location_js_1 = require("./location.js");
const MODULE_DECLARATION_NODES = new Set([
    'ImportDeclaration',
    'ExportNamedDeclaration',
    'ExportDefaultDeclaration',
    'ExportAllDeclaration',
]);
function isModuleDeclaration(node) {
    return node !== undefined && MODULE_DECLARATION_NODES.has(node.type);
}
exports.FUNCTION_NODES = [
    'FunctionDeclaration',
    'FunctionExpression',
    'ArrowFunctionExpression',
];
exports.functionLike = new Set([
    'FunctionDeclaration',
    'FunctionExpression',
    'ArrowFunctionExpression',
    'MethodDefinition',
]);
function isFunctionExpression(node) {
    return node?.type === 'FunctionExpression';
}
function isFunctionDeclaration(node) {
    return node?.type === 'FunctionDeclaration';
}
function isArrowFunctionExpression(node) {
    return node?.type === 'ArrowFunctionExpression';
}
function isIdentifier(node, ...values) {
    return node?.type === 'Identifier' && (values.length === 0 || values.includes(node.name));
}
function getProgramStatements(program) {
    return program.body.filter((node) => !isModuleDeclaration(node));
}
function isIfStatement(node) {
    return node?.type === 'IfStatement';
}
function isMemberWithProperty(node, ...values) {
    return node.type === 'MemberExpression' && isIdentifier(node.property, ...values);
}
function isThrowStatement(node) {
    return node?.type === 'ThrowStatement';
}
function isMemberExpression(node, objectValue, ...propertyValue) {
    if (node.type === 'MemberExpression') {
        const { object, property } = node;
        if (isIdentifier(object, objectValue) && isIdentifier(property, ...propertyValue)) {
            return true;
        }
    }
    return false;
}
function isLogicalExpression(node) {
    return node?.type === 'LogicalExpression';
}
function isBinaryPlus(node) {
    return node.type === 'BinaryExpression' && node.operator === '+';
}
function isArrayExpression(node) {
    return node?.type === 'ArrayExpression';
}
function isRequireModule(node, ...moduleNames) {
    if (isIdentifier(node.callee, 'require') && node.arguments.length === 1) {
        const argument = node.arguments[0];
        if (argument.type === 'Literal') {
            return moduleNames.includes(String(argument.value));
        }
    }
    return false;
}
function isMethodInvocation(callExpression, objectIdentifierName, methodName, minArgs) {
    return (callExpression.callee.type === 'MemberExpression' &&
        isIdentifier(callExpression.callee.object, objectIdentifierName) &&
        isIdentifier(callExpression.callee.property, methodName) &&
        callExpression.callee.property.type === 'Identifier' &&
        callExpression.arguments.length >= minArgs);
}
function isFunctionInvocation(callExpression, functionName, minArgs) {
    return (callExpression.callee.type === 'Identifier' &&
        isIdentifier(callExpression.callee, functionName) &&
        callExpression.arguments.length >= minArgs);
}
function isFunctionCall(node) {
    return node.type === 'CallExpression' && node.callee.type === 'Identifier';
}
function isMethodCall(callExpr) {
    return (callExpr.callee.type === 'MemberExpression' &&
        !callExpr.callee.computed &&
        callExpr.callee.property.type === 'Identifier');
}
function isCallingMethod(callExpr, arity, ...methodNames) {
    return (isMethodCall(callExpr) &&
        callExpr.arguments.length === arity &&
        methodNames.includes(callExpr.callee.property.name));
}
function isModuleExports(node) {
    return (node.type === 'MemberExpression' &&
        node.object.type === 'Identifier' &&
        node.object.name === 'module' &&
        node.property.type === 'Identifier' &&
        node.property.name === 'exports');
}
function isFunctionNode(node) {
    return exports.FUNCTION_NODES.includes(node.type);
}
// we have similar function in eslint-plugin-sonarjs, however this one accepts null
// eventually we should update eslint-plugin-sonarjs
function isLiteral(n) {
    return n?.type === 'Literal';
}
function isNullLiteral(n) {
    return isLiteral(n) && n.value === null;
}
function isFalseLiteral(n) {
    return isLiteral(n) && n.value === false;
}
function isUndefined(node) {
    return node.type === 'Identifier' && node.name === 'undefined';
}
/**
 * Detect expression statements like the following:
 *  myArray[1] = 42;
 *  myArray[1] += 42;
 *  myObj.prop1 = 3;
 *  myObj.prop1 += 3;
 */
function isElementWrite(statement, ref, recursive = true) {
    if (statement.expression?.type === 'AssignmentExpression') {
        const assignmentExpression = statement.expression;
        const lhs = assignmentExpression.left;
        return isMemberExpressionReference(lhs, ref, recursive);
    }
    return false;
}
function isMemberExpressionReference(lhs, ref, recursive = true) {
    return (lhs.type === 'MemberExpression' &&
        (isReferenceTo(ref, lhs.object) ||
            (recursive && isMemberExpressionReference(lhs.object, ref, recursive))));
}
function isReferenceTo(ref, node) {
    return node.type === 'Identifier' && node === ref.identifier;
}
function getUniqueWriteUsage(context, name, node) {
    const variable = getVariableFromName(context, name, node);
    return getUniqueWriteReference(variable);
}
function getUniqueWriteReference(variable) {
    if (variable) {
        const writeReferences = variable.references.filter(reference => reference.isWrite());
        if (writeReferences.length === 1 && writeReferences[0].writeExpr) {
            return writeReferences[0].writeExpr;
        }
    }
    return undefined;
}
function getUniqueWriteUsageOrNode(context, node, recursive = false) {
    if (node.type === 'Identifier') {
        const usage = getUniqueWriteUsage(context, node.name, node);
        if (usage) {
            return recursive ? getUniqueWriteUsageOrNode(context, usage, recursive) : usage;
        }
        else {
            return node;
        }
    }
    else {
        return node;
    }
}
function getValueOfExpression(context, expr, type, recursive = false) {
    if (!expr) {
        return undefined;
    }
    if (isNodeType(expr, type)) {
        return expr;
    }
    if (expr.type === 'Identifier') {
        const usage = getUniqueWriteUsage(context, expr.name, expr);
        if (usage) {
            if (isNodeType(usage, type)) {
                return usage;
            }
            if (recursive) {
                return getValueOfExpression(context, usage, type, true);
            }
        }
    }
    return undefined;
}
// see https://stackoverflow.com/questions/64262105/narrowing-return-value-of-function-based-on-argument
function isNodeType(node, type) {
    return node.type === type;
}
/**
 * for `x = 42` or `let x = 42` when visiting '42' returns 'x' variable
 */
function getLhsVariable(context, node) {
    const ancestors = context.sourceCode.getAncestors(node);
    const parent = (0, collection_js_1.last)(ancestors);
    let formIdentifier;
    if (parent.type === 'VariableDeclarator' && parent.id.type === 'Identifier') {
        formIdentifier = parent.id;
    }
    else if (parent.type === 'AssignmentExpression' && parent.left.type === 'Identifier') {
        formIdentifier = parent.left;
    }
    if (formIdentifier) {
        return getVariableFromName(context, formIdentifier.name, node);
    }
    return undefined;
}
function getVariableFromScope(scope, name) {
    let variable;
    while (variable == null && scope != null) {
        variable = scope.variables.find(value => value.name === name);
        scope = scope.upper;
    }
    return variable;
}
function getVariableFromName(context, name, node) {
    const scope = context.sourceCode.getScope(node);
    return getVariableFromScope(scope, name);
}
/**
 * Takes array of arguments. Keeps following variable definitions
 * and unpacking arrays as long as possible. Returns flattened
 * array with all collected nodes.
 *
 * A usage example should clarify why this might be useful.
 * According to ExpressJs `app.use` spec, the arguments can be:
 *
 * - A middleware function.
 * - A series of middleware functions (separated by commas).
 * - An array of middleware functions.
 * - A combination of all of the above.
 *
 * This means that methods like `app.use` accept variable arguments,
 * but also arrays, or combinations thereof. This methods helps
 * to flatten out such complicated composed argument lists.
 */
function flattenArgs(context, args) {
    // Invokes `getUniqueWriteUsageOrNode` at most once, from then on
    // only flattens arrays.
    function recHelper(nodePossiblyIdentifier) {
        const n = getUniqueWriteUsageOrNode(context, nodePossiblyIdentifier);
        if (n.type === 'ArrayExpression') {
            return (0, collection_js_1.flatMap)(n.elements, recHelper);
        }
        else {
            return [n];
        }
    }
    return (0, collection_js_1.flatMap)(args, recHelper);
}
function resolveIdentifiers(node, acceptShorthand = false) {
    const identifiers = [];
    resolveIdentifiersAcc(node, identifiers, acceptShorthand);
    return identifiers;
}
function resolveIdentifiersAcc(node, identifiers, acceptShorthand) {
    if (!node) {
        return;
    }
    switch (node.type) {
        case 'Identifier':
            identifiers.push(node);
            break;
        case 'ObjectPattern':
            for (const prop of node.properties) {
                resolveIdentifiersAcc(prop, identifiers, acceptShorthand);
            }
            break;
        case 'ArrayPattern':
            for (const elem of node.elements) {
                elem && resolveIdentifiersAcc(elem, identifiers, acceptShorthand);
            }
            break;
        case 'Property':
            if (acceptShorthand || !node.shorthand) {
                resolveIdentifiersAcc(node.value, identifiers, acceptShorthand);
            }
            break;
        case 'RestElement':
            resolveIdentifiersAcc(node.argument, identifiers, acceptShorthand);
            break;
        case 'AssignmentPattern':
            resolveIdentifiersAcc(node.left, identifiers, acceptShorthand);
            break;
        case 'TSParameterProperty':
            resolveIdentifiersAcc(node.parameter, identifiers, acceptShorthand);
            break;
    }
}
function getPropertyWithValue(context, objectExpression, propertyName, propertyValue) {
    const maybeProperty = getProperty(objectExpression, propertyName, context);
    if (maybeProperty) {
        const maybePropertyValue = getValueOfExpression(context, maybeProperty.value, 'Literal');
        if (maybePropertyValue?.value === propertyValue) {
            return maybeProperty;
        }
    }
    return undefined;
}
function getPropertyFromSpreadElement(spreadElement, key, ctx) {
    const props = getValueOfExpression(ctx, spreadElement.argument, 'ObjectExpression');
    const recursiveDefinition = (0, ancestor_js_1.findFirstMatchingAncestor)(spreadElement.argument, node => node === props);
    if (recursiveDefinition || props === undefined) {
        return undefined;
    }
    return getProperty(props, key, ctx);
}
/**
 * Retrieves the property with the specified key from the given node.
 * @returns The property if found, or null if not found, or undefined if property not found and one of the properties
 * is an unresolved SpreadElement.
 */
function getProperty(expr, key, ctx) {
    if (expr?.type !== 'ObjectExpression') {
        return null;
    }
    let unresolvedSpreadElement = false;
    for (let i = expr.properties.length - 1; i >= 0; --i) {
        const property = expr.properties[i];
        if (isProperty(property, key)) {
            return property;
        }
        if (property.type === 'SpreadElement') {
            const prop = getPropertyFromSpreadElement(property, key, ctx);
            if (prop === undefined) {
                unresolvedSpreadElement = true;
            }
            else if (prop !== null) {
                return prop;
            }
        }
    }
    if (unresolvedSpreadElement) {
        return undefined;
    }
    return null;
    function isProperty(node, key) {
        return (node.type === 'Property' &&
            (isIdentifier(node.key, key) || (isStringLiteral(node.key) && node.key.value === key)));
    }
}
function resolveFromFunctionReference(context, functionIdentifier) {
    const { scopeManager } = context.sourceCode;
    for (const scope of scopeManager.scopes) {
        const reference = scope.references.find(r => r.identifier === functionIdentifier);
        if (reference?.resolved?.defs.length === 1 &&
            reference.resolved.defs[0].type === 'FunctionName') {
            return reference.resolved.defs[0].node;
        }
    }
    return null;
}
function resolveFunction(context, node) {
    if (isFunctionNode(node)) {
        return node;
    }
    else if (node.type === 'Identifier') {
        return resolveFromFunctionReference(context, node);
    }
    else {
        return null;
    }
}
function checkSensitiveCall(context, callExpression, sensitiveArgumentIndex, sensitiveProperty, sensitivePropertyValue, message) {
    if (callExpression.arguments.length < sensitiveArgumentIndex + 1) {
        return;
    }
    const sensitiveArgument = callExpression.arguments[sensitiveArgumentIndex];
    const options = getValueOfExpression(context, sensitiveArgument, 'ObjectExpression');
    if (!options) {
        return;
    }
    const unsafeProperty = getPropertyWithValue(context, options, sensitiveProperty, sensitivePropertyValue);
    if (unsafeProperty) {
        (0, location_js_1.report)(context, {
            node: callExpression.callee,
            message,
        }, [(0, location_js_1.toSecondaryLocation)(unsafeProperty)]);
    }
}
function isStringLiteral(node) {
    return isLiteral(node) && typeof node.value === 'string';
}
function isBooleanLiteral(node) {
    return isLiteral(node) && typeof node.value === 'boolean';
}
function isNumberLiteral(node) {
    return isLiteral(node) && typeof node.value === 'number';
}
function isRegexLiteral(node) {
    return node.type === 'Literal' && node.value instanceof RegExp;
}
/**
 * Checks if the node is of the form: foo.bar
 *
 * @param node
 * @returns
 */
function isDotNotation(node) {
    return node.type === 'MemberExpression' && !node.computed && node.property.type === 'Identifier';
}
/**
 * Checks if the node is of the form: foo["bar"]
 *
 * @param node
 * @returns
 */
function isIndexNotation(node) {
    return node.type === 'MemberExpression' && node.computed && isStringLiteral(node.property);
}
function isObjectDestructuring(node) {
    return ((node.type === 'VariableDeclarator' && node.id.type === 'ObjectPattern') ||
        (node.type === 'AssignmentExpression' && node.left.type === 'ObjectPattern'));
}
function isStaticTemplateLiteral(node) {
    return (node.type === 'TemplateLiteral' && node.expressions.length === 0 && node.quasis.length === 1);
}
// Test for raw expressions like: String.raw`c:\foo\bar.txt` that corresponds to 'c:\\foo\\bar.txt'
function isSimpleRawString(node) {
    return (node.type === 'TaggedTemplateExpression' &&
        isDotNotation(node.tag) &&
        isIdentifier(node.tag.object, 'String') &&
        isIdentifier(node.tag.property, 'raw') &&
        isStaticTemplateLiteral(node.quasi));
}
// In simple raw strings, the literal value is: node.quasi.quasis[0].value.raw
// This function fails if isSimpleRawString() is not returning true for the node.
function getSimpleRawStringValue(node) {
    return node.quasi.quasis[0].value.raw;
}
function isThisExpression(node) {
    return node.type === 'ThisExpression';
}
function isProperty(node) {
    return node.type === 'Property';
}
/**
 * Check if an identifier has no known value, meaning:
 *
 * - It's not imported/required
 * - Defined variable without any write references (function parameter?)
 * - Non-defined variable (a possible global?)
 *
 * @param node Node to check
 * @param ctx Rule context
 */
function isUnresolved(node, ctx) {
    if (!node || (0, module_js_1.getFullyQualifiedName)(ctx, node) || isUndefined(node)) {
        return false;
    }
    let nodeToCheck = node;
    while (nodeToCheck.type === 'MemberExpression') {
        nodeToCheck = nodeToCheck.object;
    }
    if (nodeToCheck.type === 'Identifier') {
        const variable = getVariableFromName(ctx, nodeToCheck.name, node);
        const writeReferences = variable?.references.filter(reference => reference.isWrite());
        if (!variable || !writeReferences?.length) {
            return true;
        }
    }
    return false;
}
function hasParent(node) {
    return 'parent' in node && node.parent !== null;
}
/**
 * Checks if a function node has a type predicate return type (`: x is Type`).
 */
function hasTypePredicateReturn(node) {
    if (isFunctionNode(node)) {
        const tsNode = node;
        return tsNode.returnType?.typeAnnotation?.type === 'TSTypePredicate';
    }
    return false;
}
