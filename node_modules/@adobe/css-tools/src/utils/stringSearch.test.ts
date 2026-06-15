import {
  indexOfArrayNonEscaped,
  indexOfArrayWithBracketAndQuoteSupport,
  MAX_LOOP,
  splitWithBracketAndQuoteSupport,
} from './stringSearch';

describe('indexOfArrayNonEscaped', () => {
  it('should find first non-escaped occurrence', () => {
    expect(indexOfArrayNonEscaped('abc def', ['d'])).toBe(4);
    expect(indexOfArrayNonEscaped('abc \\def ghi def', ['d'])).toBe(13);
  });

  it('should handle multiple search strings', () => {
    expect(indexOfArrayNonEscaped('abc def ghi', ['d', 'g'])).toBe(4);
    expect(indexOfArrayNonEscaped('abc ghi def', ['d', 'g'])).toBe(4);
  });

  it('should return -1 when not found', () => {
    expect(indexOfArrayNonEscaped('abc def', ['x'])).toBe(-1);
    expect(indexOfArrayNonEscaped('abc \\xyz def', ['x'])).toBe(-1);
  });

  it('should respect start position', () => {
    expect(indexOfArrayNonEscaped('abc def def', ['def'], 5)).toBe(8);
  });

  it('should throw error on too many escapes', () => {
    const tooManyEscapes = '\\a\\b\\c\\d'.repeat(MAX_LOOP / 2);
    expect(() => indexOfArrayNonEscaped(tooManyEscapes, ['x'])).toThrow(
      'Too many escaping',
    );
  });
});

describe('indexOfArrayWithBracketAndQuoteSupport', () => {
  it('should find first non-escaped occurrence', () => {
    expect(indexOfArrayWithBracketAndQuoteSupport('abc def', ['d'])).toBe(4);
    expect(
      indexOfArrayWithBracketAndQuoteSupport('abc \\def ghi def', ['d']),
    ).toBe(13);
  });

  it('should handle brackets correctly', () => {
    expect(indexOfArrayWithBracketAndQuoteSupport('abc (def) ghi', ['g'])).toBe(
      10,
    );
    expect(
      indexOfArrayWithBracketAndQuoteSupport('abc (d(e)f) ghi', ['g']),
    ).toBe(12);
    expect(indexOfArrayWithBracketAndQuoteSupport('abc (def ghi', ['g'])).toBe(
      -1,
    );
  });

  it('should handle double quotes correctly', () => {
    expect(indexOfArrayWithBracketAndQuoteSupport('abc "def" ghi', ['g'])).toBe(
      10,
    );
    expect(
      indexOfArrayWithBracketAndQuoteSupport('abc "d\\"ef" ghi', ['g']),
    ).toBe(12);
    expect(indexOfArrayWithBracketAndQuoteSupport('abc "def ghi', ['g'])).toBe(
      -1,
    );
  });

  it('should handle single quotes correctly', () => {
    expect(indexOfArrayWithBracketAndQuoteSupport("abc 'def' ghi", ['g'])).toBe(
      10,
    );
    expect(
      indexOfArrayWithBracketAndQuoteSupport("abc 'd\\'ef' ghi", ['g']),
    ).toBe(12);
    expect(indexOfArrayWithBracketAndQuoteSupport("abc 'def ghi", ['g'])).toBe(
      -1,
    );
  });

  it('should handle multiple search strings', () => {
    expect(
      indexOfArrayWithBracketAndQuoteSupport('abc def ghi', ['d', 'g']),
    ).toBe(4);
    expect(
      indexOfArrayWithBracketAndQuoteSupport('abc (def) ghi', ['d', 'g']),
    ).toBe(10);
  });

  it('should throw error on too many escapes or nested structures', () => {
    const tooManyEscapes = '\\a\\b\\c\\d'.repeat(MAX_LOOP / 2);
    expect(() =>
      indexOfArrayWithBracketAndQuoteSupport(tooManyEscapes, ['x']),
    ).toThrow('Too many escaping');

    const tooManyBrackets = '()'.repeat(MAX_LOOP + 1);
    expect(() =>
      indexOfArrayWithBracketAndQuoteSupport(tooManyBrackets, [')']),
    ).toThrow('Too many escaping');
  });
});

describe('splitWithBracketAndQuoteSupport', () => {
  test('splits string by search tokens', () => {
    expect(splitWithBracketAndQuoteSupport('a,b', [','])).toEqual(['a', 'b']);
  });

  test('respects brackets', () => {
    expect(splitWithBracketAndQuoteSupport('a,(b,c)', [','])).toEqual([
      'a',
      '(b,c)',
    ]);
  });

  test('respects double quotes', () => {
    expect(splitWithBracketAndQuoteSupport('a,"b,c"', [','])).toEqual([
      'a',
      '"b,c"',
    ]);
  });

  test('respects single quotes', () => {
    expect(splitWithBracketAndQuoteSupport("a,'b,c'", [','])).toEqual([
      'a',
      "'b,c'",
    ]);
  });

  test('handles multiple search tokens', () => {
    expect(splitWithBracketAndQuoteSupport('a;b,c', [';', ','])).toEqual([
      'a',
      'b',
      'c',
    ]);
  });

  test('handles empty strings', () => {
    expect(splitWithBracketAndQuoteSupport('', [','])).toEqual([]);
  });
});
