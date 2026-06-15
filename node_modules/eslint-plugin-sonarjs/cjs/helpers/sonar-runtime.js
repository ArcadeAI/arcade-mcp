"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.isSonarRuntime = isSonarRuntime;
function isSonarRuntime(context) {
    return context.settings.sonarRuntime ? context.settings.sonarRuntime : false;
}
