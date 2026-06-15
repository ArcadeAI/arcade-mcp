"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.LiveVariables = void 0;
exports.lva = lva;
function lva(liveVariablesMap) {
    const worklist = Array.from(liveVariablesMap.values(), lva => lva.segment);
    while (worklist.length > 0) {
        const current = worklist.pop();
        const liveVariables = liveVariablesMap.get(current.id);
        const liveInHasChanged = liveVariables.propagate(liveVariablesMap);
        if (liveInHasChanged) {
            for (const prev of current.prevSegments) {
                worklist.push(prev);
            }
        }
    }
}
class LiveVariables {
    constructor(segment) {
        /**
         * variables that are being read in the block
         */
        this.gen = new Set();
        /**
         * variables that are being written in the block
         */
        this.kill = new Set();
        /**
         * variables needed by this or a successor block and are not killed in this block
         */
        this.in = new Set();
        /**
         * variables needed by successors
         */
        this.out = [];
        /**
         * collects references in order they are evaluated, set in JS maintains insertion order
         */
        this.references = new Set();
        this.segment = segment;
    }
    add(ref) {
        const variable = ref.resolved;
        if (variable) {
            if (ref.isRead()) {
                this.gen.add(variable);
            }
            if (ref.isWrite()) {
                this.kill.add(variable);
            }
            this.references.add(ref);
        }
    }
    propagate(liveVariablesMap) {
        const out = [];
        for (const next of this.segment.nextSegments) {
            out.push(...liveVariablesMap.get(next.id).in);
        }
        const diff = difference(out, this.kill);
        this.out = out;
        if (shouldUpdate(this.in, this.gen, diff)) {
            this.in = new Set([...this.gen, ...diff]);
            return true;
        }
        else {
            return false;
        }
    }
}
exports.LiveVariables = LiveVariables;
function difference(a, b) {
    if (b.size === 0) {
        return a;
    }
    const diff = [];
    for (const e of a) {
        if (!b.has(e)) {
            diff.push(e);
        }
    }
    return diff;
}
function shouldUpdate(inSet, gen, diff) {
    for (const e of gen) {
        if (!inSet.has(e)) {
            return true;
        }
    }
    for (const e of diff) {
        if (!inSet.has(e)) {
            return true;
        }
    }
    return false;
}
