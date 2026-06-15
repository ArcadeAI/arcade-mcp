"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.AwsCdkTemplate = AwsCdkTemplate;
exports.AwsCdkCheckArguments = AwsCdkCheckArguments;
exports.getLiteralValue = getLiteralValue;
exports.normalizeFQN = normalizeFQN;
const module_js_1 = require("../module.js");
const ast_js_1 = require("../ast.js");
const AWS_OPTIONS_ARGUMENT_POSITION = 2;
/**
 * A rule template for AWS CDK resources
 *
 * @param mapOrFactory callbacks to invoke when a new expression or a call expression matches a fully qualified name
 * @param meta the rule metadata
 * @returns the instantiated rule module
 */
function AwsCdkTemplate(mapOrFactory, meta = {}) {
    return {
        meta,
        create(ctx) {
            const consumers = typeof mapOrFactory === 'function' ? mapOrFactory(ctx) : mapOrFactory;
            return {
                'NewExpression, CallExpression'(node) {
                    if (node.arguments.some(arg => arg.type === 'SpreadElement')) {
                        return;
                    }
                    for (const fqn in consumers) {
                        const normalizedExpectedFQN = normalizeFQN(fqn);
                        const callback = consumers[fqn];
                        if (typeof callback === 'object' || node.type === 'CallExpression') {
                            executeIfMatching(node, normalizedExpectedFQN, callback);
                            continue;
                        }
                        const normalizedActualFQN = normalizeFQN((0, module_js_1.getFullyQualifiedName)(ctx, node.callee));
                        if (normalizedActualFQN === normalizedExpectedFQN) {
                            callback(node, ctx);
                        }
                    }
                },
            };
            function executeIfMatching(node, expected, callback) {
                if (typeof callback === 'function') {
                    return;
                }
                const fqn = normalizeFQN((0, module_js_1.getFullyQualifiedName)(ctx, node.callee));
                if (node.type === 'NewExpression' && fqn === expected) {
                    callback.newExpression?.(node, ctx);
                }
                else if (isMethodCall(callback, fqn, expected)) {
                    callback.callExpression(node, ctx, fqn);
                }
            }
        },
    };
}
/**
 * Get the messageId at the given position from an array. If a string is used
 * instead of an array, return it
 * @param messageId Array of messageIds or single string if only one messageId is used
 * @param pos
 */
function getMessageAtPos(messageId, pos = 0) {
    if (typeof messageId === 'string') {
        return messageId;
    }
    return messageId[pos];
}
/**
 * Function to analyse arguments in a function and check for correct values. It will report if the
 * conditions are not met unless `silent = true`, in which case it will return boolean `true`
 * indicating conditions are not met.
 *
 * @param messageId Array of messageIds or single string if only one messageId is used. When an array is passed,
 *                  first messageId is used for omitted values and second for invalid values.
 * @param needsProps whether default (undefined) values are allowed or if it must be set
 * @param propertyName property name to search in the object (Array of strings for nested props)
 * @param values allowed or disallowed values
 * @param silent whether the function must report or just return conflicting Node when conditions are not met
 * @param position position of the argument to be analysed (3rd argument by default)
 */
function AwsCdkCheckArguments(messageId, needsProps, propertyName, values, silent = false, position = AWS_OPTIONS_ARGUMENT_POSITION) {
    return (expr, ctx) => {
        const argument = expr.arguments[position];
        // Argument not found or undefined
        if (!argument || (0, ast_js_1.isUndefined)(argument)) {
            if (needsProps) {
                if (silent) {
                    return expr.callee;
                }
                ctx.report({ messageId: getMessageAtPos(messageId, 0), node: expr.callee });
            }
            return;
        }
        const properties = traverseProperties({ node: argument, nodeToReport: argument }, typeof propertyName === 'string' ? [propertyName] : propertyName, ctx, getMessageAtPos(messageId, 0), needsProps, silent);
        if (!Array.isArray(properties)) {
            return properties;
        }
        if (!properties?.length) {
            return;
        }
        for (const property of properties) {
            const propertyValue = (0, ast_js_1.getUniqueWriteUsageOrNode)(ctx, property.node.value, true);
            if ((0, ast_js_1.isUnresolved)(propertyValue, ctx)) {
                continue;
            }
            /* Property is undefined or an empty array, which is the undefined equivalent
               for properties with an array-form where we expect multiple nested values */
            if ((0, ast_js_1.isUndefined)(propertyValue) ||
                (propertyValue.type === 'ArrayExpression' && !propertyValue.elements.length)) {
                if (needsProps) {
                    if (silent) {
                        return getNodeToReport(property);
                    }
                    ctx.report({ messageId: getMessageAtPos(messageId, 0), node: getNodeToReport(property) });
                }
                continue;
            }
            // Value is expected to be a primitive (string, number)
            if (values?.primitives && disallowedValue(ctx, propertyValue, values.primitives)) {
                if (silent) {
                    return getNodeToReport(property);
                }
                ctx.report({ messageId: getMessageAtPos(messageId, 1), node: getNodeToReport(property) });
            }
            // Value is expected to be an Identifier following a specific FQN
            if (values?.fqns && disallowedFQNs(ctx, propertyValue, values.fqns)) {
                if (silent) {
                    return getNodeToReport(property);
                }
                ctx.report({ messageId: getMessageAtPos(messageId, 1), node: getNodeToReport(property) });
            }
            // The value needs to be validated with a customized function
            if (values?.customChecker?.(ctx, propertyValue)) {
                if (silent) {
                    return getNodeToReport(property);
                }
                ctx.report({ messageId: getMessageAtPos(messageId, 1), node: getNodeToReport(property) });
            }
        }
    };
}
function getNodeToReport(property) {
    if (property.nodeToReport.type === 'Property') {
        return property.nodeToReport.value;
    }
    return property.nodeToReport;
}
/**
 * Given an object expression, check for [nested] attributes. If at some level an
 * array is found, the search for next level properties will be performed on each element
 * of the array.
 *
 * @returns an array of Nodes which have the given property path.
 *
 * @param node node to look for the next property.
 * @param propertyPath pending property paths to traverse
 * @param ctx rule context
 * @param messageId messageId to report when path cannot be met and silent = `false`
 * @param needsProp whether missing (undefined) values are allowed or if it must be set
 * @param silent whether the function must report or just return conflicting Node when conditions are not met
 */
function traverseProperties(node, propertyPath, ctx, messageId, needsProp, silent) {
    const [propertyName, ...nextElements] = propertyPath;
    const properties = [];
    const children = [];
    if ((0, ast_js_1.isUnresolved)(node.node, ctx)) {
        return [];
    }
    const objExpr = (0, ast_js_1.getValueOfExpression)(ctx, node.node, 'ObjectExpression', true);
    if (objExpr === undefined) {
        const arrayExpr = (0, ast_js_1.getValueOfExpression)(ctx, node.node, 'ArrayExpression', true);
        if (!arrayExpr?.elements.length) {
            if (needsProp) {
                if (silent) {
                    return node.nodeToReport;
                }
                ctx.report({ messageId, node: node.nodeToReport });
            }
            return [];
        }
        for (const element of arrayExpr.elements) {
            const elemObjExpr = (0, ast_js_1.getValueOfExpression)(ctx, element, 'ObjectExpression', true);
            if (elemObjExpr && element) {
                children.push({ node: elemObjExpr, nodeToReport: element });
            }
        }
    }
    else {
        children.push({ node: objExpr, nodeToReport: node.nodeToReport });
    }
    for (const child of children) {
        const property = (0, ast_js_1.getProperty)(child.node, propertyName, ctx);
        if (property === undefined) {
            continue;
        }
        if (!property) {
            if (needsProp) {
                if (silent) {
                    return node.nodeToReport;
                }
                ctx.report({ messageId, node: node.nodeToReport });
            }
            continue;
        }
        if (nextElements.length) {
            if (child.node === child.nodeToReport &&
                child.node.properties.includes(property)) {
                child.nodeToReport = property.value;
            }
            child.node = property.value;
            const nextElementChildren = traverseProperties(child, nextElements, ctx, messageId, needsProp, silent);
            if (!Array.isArray(nextElementChildren)) {
                return nextElementChildren;
            }
            properties.push(...nextElementChildren);
        }
        else {
            if (child.node === child.nodeToReport &&
                child.node.properties.includes(property)) {
                child.nodeToReport = property;
            }
            child.node = property;
            properties.push(child);
        }
    }
    return properties;
}
function disallowedValue(ctx, node, values) {
    const literal = getLiteralValue(ctx, node);
    if (literal) {
        if (values.valid?.length) {
            const found = values.valid.some(value => {
                if (values.case_insensitive && typeof literal.value === 'string') {
                    return value.toLowerCase() === literal.value.toLowerCase();
                }
                return value === literal.value;
            });
            if (!found) {
                return true;
            }
        }
        if (values.invalid?.length) {
            const found = values.invalid.some(value => {
                if (values.case_insensitive && typeof literal.value === 'string') {
                    return value.toLowerCase() === literal.value.toLowerCase();
                }
                return value === literal.value;
            });
            if (found) {
                return true;
            }
        }
    }
    return false;
}
function getLiteralValue(ctx, node) {
    if ((0, ast_js_1.isLiteral)(node)) {
        return node;
    }
    else if ((0, ast_js_1.isIdentifier)(node)) {
        const usage = (0, ast_js_1.getUniqueWriteUsage)(ctx, node.name, node);
        if (usage) {
            return getLiteralValue(ctx, usage);
        }
    }
    return undefined;
}
function disallowedFQNs(ctx, node, values) {
    const normalizedFQN = normalizeFQN((0, module_js_1.getFullyQualifiedName)(ctx, node));
    if (values.valid?.length &&
        (!normalizedFQN || !values.valid.map(normalizeFQN).includes(normalizedFQN))) {
        return true;
    }
    return normalizedFQN && values.invalid?.map(normalizeFQN).includes(normalizedFQN);
}
function isMethodCall(callback, fqn, expected) {
    if (callback.functionName) {
        return fqn === `${expected}.${callback.functionName}`;
    }
    else if (callback.methods && fqn?.startsWith(expected)) {
        const methodNames = fqn.substring(expected.length).split('.');
        const methods = callback.methods;
        return methodNames.every(name => name === '' || methods.includes(name));
    }
    else {
        return fqn === expected;
    }
}
function normalizeFQN(fqn) {
    return fqn?.replaceAll('-', '_');
}
