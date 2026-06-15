"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.toInternalMetricsSettings = toInternalMetricsSettings;
exports.getInternalMetricsSink = getInternalMetricsSink;
const SONAR_INTERNAL_SETTINGS_KEY = 'sonarInternal';
const SONAR_INTERNAL_METRICS_SINK_KEY = 'metricsSink';
function toInternalMetricsSettings(metricsSink) {
    return {
        [SONAR_INTERNAL_SETTINGS_KEY]: {
            [SONAR_INTERNAL_METRICS_SINK_KEY]: metricsSink,
        },
    };
}
function getInternalMetricsSink(settings) {
    if (!settings || typeof settings !== 'object') {
        return undefined;
    }
    const sonarInternal = settings[SONAR_INTERNAL_SETTINGS_KEY];
    if (!sonarInternal || typeof sonarInternal !== 'object') {
        return undefined;
    }
    const metricsSink = sonarInternal[SONAR_INTERNAL_METRICS_SINK_KEY];
    if (!metricsSink || typeof metricsSink !== 'object') {
        return undefined;
    }
    return metricsSink;
}
