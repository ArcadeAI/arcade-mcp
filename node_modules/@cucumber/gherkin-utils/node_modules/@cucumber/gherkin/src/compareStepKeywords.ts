/**
 * Compares two step keywords based on length. Can be used with Array.sort to
 * sort keywords by length, descending.
 *
 * @param a - the first step keyword
 * @param b - the second step keyword
 */
export function compareStepKeywords(a: string, b: string): number {
    return b.length - a.length
}
