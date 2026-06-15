/**
Check if a string has [ANSI escape codes](https://en.wikipedia.org/wiki/ANSI_escape_code).

@example
```
import hasAnsi from 'has-ansi';

hasAnsi('\u001B[4mUnicorn\u001B[0m');
//=> true

hasAnsi('cake');
//=> false
```
*/
export default function hasAnsi(string: string): boolean;
