"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.copyingSortLike = exports.sortLike = exports.writingMethods = exports.collectionConstructor = void 0;
exports.flatMap = flatMap;
exports.last = last;
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
exports.collectionConstructor = ['Array', 'Map', 'Set', 'WeakSet', 'WeakMap'];
exports.writingMethods = [
    // array methods
    'copyWithin',
    'fill',
    'pop',
    'push',
    'reverse',
    'set',
    'shift',
    'sort',
    'splice',
    'unshift',
    // map, set methods
    'add',
    'clear',
    'delete',
];
exports.sortLike = ['sort', '"sort"', "'sort'"];
exports.copyingSortLike = ['toSorted', '"toSorted"', "'toSorted'"];
function flatMap(xs, f) {
    const acc = [];
    for (const x of xs) {
        acc.push(...f(x));
    }
    return acc;
}
function last(arr) {
    return arr.at(-1);
}
