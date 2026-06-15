"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.encodeContents = encodeContents;
exports.toSecondaryLocation = toSecondaryLocation;
exports.report = report;
exports.expandMessage = expandMessage;
exports.getMainFunctionTokenLocation = getMainFunctionTokenLocation;
exports.getFirstTokenAfter = getFirstTokenAfter;
exports.getFirstToken = getFirstToken;
function encodeContents(message, secondaryLocations, cost) {
    return JSON.stringify({
        message,
        secondaryLocations,
        cost,
    });
}
/**
 * Encodes an ESLint descriptor message with secondary locations
 *
 * The encoding consists in stringifying a JavaScript object with
 * `JSON.stringify` that includes the ESLint's descriptor message
 * along with second location information: message and location.
 *
 * This encoded message is eventually decoded by the linter wrapper
 * on the condition that the rule definition of the flagged problem
 * defines the internal `sonar-runtime` parameter in its schema.
 *
 * @param reportDescriptor the ESLint report descriptor
 * @param secondaryLocations the secondary locations
 * @param cost the optional cost to fix
 * @returns the encoded message with secondary locations
 */
function toEncodedMessage(reportDescriptor, secondaryLocations, cost) {
    if (!('message' in reportDescriptor)) {
        throw new Error('Field "message" is mandatory in the report descriptor for sonar runtime encoding');
    }
    reportDescriptor.data ??= {};
    const { message: _, ...rest } = reportDescriptor;
    return {
        ...rest,
        messageId: 'sonarRuntime',
        data: {
            sonarRuntimeData: encodeContents(expandMessage(reportDescriptor.message, reportDescriptor.data), secondaryLocations, cost),
            ...reportDescriptor.data,
        },
    };
}
function toSecondaryLocation(startLoc, endLoc = startLoc, message) {
    if (!startLoc.loc) {
        throw new Error('Invalid secondary location');
    }
    const endLocation = typeof endLoc !== 'string' && endLoc.loc ? endLoc.loc : startLoc.loc;
    return {
        message: typeof endLoc === 'string' ? endLoc : message,
        column: startLoc.loc.start.column,
        line: startLoc.loc.start.line,
        endColumn: endLocation.end.column,
        endLine: endLocation.end.line,
    };
}
/**
 * Wrapper for `context.report`, supporting secondary locations and cost.
 * Encode those extra information in the issue message when rule is executed
 * in Sonar* environment.
 */
function report(context, reportDescriptor, secondaryLocations = [], cost) {
    if (context.settings.sonarRuntime) {
        context.report(toEncodedMessage(reportDescriptor, secondaryLocations, cost));
    }
    else if ('message' in reportDescriptor && 'messageId' in reportDescriptor) {
        const { message: _, ...rest } = reportDescriptor;
        context.report(rest);
    }
    else if ('message' in reportDescriptor && 'data' in reportDescriptor) {
        const { data, ...rest } = reportDescriptor;
        context.report({
            ...rest,
            message: expandMessage(rest.message, data),
        });
    }
    else {
        context.report(reportDescriptor);
    }
}
function expandMessage(message, reportDescriptorData) {
    let expandedMessage = message;
    if (reportDescriptorData !== undefined) {
        for (const [key, value] of Object.entries(reportDescriptorData)) {
            expandedMessage = replaceAll(expandedMessage, `{{${key}}}`, value.toString());
        }
    }
    return expandedMessage;
}
function replaceAll(target, search, replacement) {
    return target.split(search).join(replacement);
}
/**
 * Returns a location of the "main" function token:
 * - function name for a function declaration, method or accessor
 * - "function" keyword for a function expression
 * - "=>" for an arrow function
 */
function getMainFunctionTokenLocation(fn, parent, context) {
    let location;
    if (fn.type === 'FunctionDeclaration') {
        // `fn.id` can be null when it is `export default function` (despite of the @types/TSESTree definition)
        if (fn.id) {
            location = fn.id.loc;
        }
        else {
            const token = getTokenByValue(fn, 'function', context);
            location = token?.loc;
        }
    }
    else if (fn.type === 'FunctionExpression') {
        if (parent && (parent.type === 'MethodDefinition' || parent.type === 'Property')) {
            location = parent.key.loc;
        }
        else {
            const token = getTokenByValue(fn, 'function', context);
            location = token?.loc;
        }
    }
    else if (fn.type === 'ArrowFunctionExpression') {
        const token = context.sourceCode
            .getTokensBefore(fn.body)
            .reverse()
            .find(token => token.value === '=>');
        location = token?.loc;
    }
    return location;
}
function getTokenByValue(node, value, context) {
    return context.sourceCode.getTokens(node).find(token => token.value === value);
}
function getFirstTokenAfter(node, context) {
    return context.sourceCode.getTokenAfter(node);
}
function getFirstToken(node, context) {
    return context.sourceCode.getTokens(node)[0];
}
