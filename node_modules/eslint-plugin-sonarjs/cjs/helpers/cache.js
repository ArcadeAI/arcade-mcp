"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ComputedCache = void 0;
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
class ComputedCache {
    constructor(computeFn) {
        this.computeFn = computeFn;
        this.cache = new Map();
    }
    get(key, context) {
        if (this.cache.has(key)) {
            return this.cache.get(key);
        }
        const value = this.computeFn(key, context);
        this.cache.set(key, value);
        return value;
    }
    set(key, value) {
        this.cache.set(key, value);
    }
    has(key) {
        return this.cache.has(key);
    }
    delete(key) {
        return this.cache.delete(key);
    }
    clear() {
        this.cache.clear();
    }
    get size() {
        return this.cache.size;
    }
}
exports.ComputedCache = ComputedCache;
