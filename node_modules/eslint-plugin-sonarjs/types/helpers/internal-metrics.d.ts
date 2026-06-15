export interface InternalMetricsSink {
    cognitiveComplexity?: number;
}
export declare function toInternalMetricsSettings(metricsSink: InternalMetricsSink): Record<string, unknown>;
export declare function getInternalMetricsSink(settings: unknown): InternalMetricsSink | undefined;
