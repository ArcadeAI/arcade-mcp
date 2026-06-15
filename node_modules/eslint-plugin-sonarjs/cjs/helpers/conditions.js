"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.collectIfBranches = collectIfBranches;
exports.collectSwitchBranches = collectSwitchBranches;
exports.takeWithoutBreak = takeWithoutBreak;
const collection_js_1 = require("./collection.js");
/** Returns a list of statements corresponding to a `if - else if - else` chain */
function collectIfBranches(node) {
    const branches = [node.consequent];
    let endsWithElse = false;
    let statement = node.alternate;
    while (statement) {
        if (statement.type === 'IfStatement') {
            branches.push(statement.consequent);
            statement = statement.alternate;
        }
        else {
            branches.push(statement);
            endsWithElse = true;
            break;
        }
    }
    return { branches, endsWithElse };
}
/** Returns a list of `switch` clauses (both `case` and `default`) */
function collectSwitchBranches(node) {
    let endsWithDefault = false;
    const branches = node.cases
        .filter((clause, index) => {
        if (!clause.test) {
            endsWithDefault = true;
        }
        // if a branch has no implementation, it's fall-through and it should not be considered
        // the only exception is the last case
        const isLast = index === node.cases.length - 1;
        return isLast || clause.consequent.length > 0;
    })
        .map(clause => takeWithoutBreak(clause.consequent));
    return { branches, endsWithDefault };
}
/** Excludes the break statement from the list */
function takeWithoutBreak(nodes) {
    return nodes.length > 0 && (0, collection_js_1.last)(nodes).type === 'BreakStatement' ? nodes.slice(0, -1) : nodes;
}
