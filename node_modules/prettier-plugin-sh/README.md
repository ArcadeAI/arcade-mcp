<p align="center">
  <img src="https://raw.githubusercontent.com/un-ts/prettier/master/assets/sh.png" height="100" />
</p>

# prettier-plugin-sh ![npm bundle size](https://img.shields.io/bundlephobia/min/prettier-plugin-sh) ![npm bundle size](https://img.shields.io/bundlephobia/minzip/prettier-plugin-sh)

> An opinionated `shellscript` formatter plugin for [Prettier][], also support simple format of `Dockerfile`, `properties`, `gitignore`, `dotenv`, `hosts`, `jvmoptions`...

Prettier is an opinionated code formatter. It enforces a consistent style by parsing your code and re-printing, taking various rules into account.

This plugin adds support for various file formats through [mvdan-sh][] via [sh-syntax][] and [dockerfmt][].

## Notice

This plugin is still under development, its printer just wraps [mvdan-sh][]'s default printer with powered by [sh-syntax][].
Of course it should just work, but may not match [prettier][]'s format sometimes.

> [!WARNING]
>
> `ignore` files are not officially supported by [mvdan-sh][] what means only basic and simple `ignore` usage cases can be handled correctly.
> We cannot do much on our side. See also <https://github.com/un-ts/prettier/issues/336>.

## Requirements

`prettier-plugin-sh` is an evergreen module. 🌲 This module requires an [LTS](https://github.com/nodejs/Release) Node version (v16.0.0+).

## Install

Using npm:

```sh
# npm
npm i -D prettier prettier-plugin-sh

# yarn
yarn add -D prettier prettier-plugin-sh
```

## Usage

Once installed, [Prettier plugins](https://prettier.io/docs/en/plugins.html) must be added to `.prettierrc`:

```json
{
  "plugins": ["prettier-plugin-sh"]
}
```

Then:

```sh
# npx
npx prettier --write script.sh

# yarn
yarn prettier --write script.sh
```

## Parser Options

```ts
interface ShOptions {
  // parser
  /**
   * KeepComments makes the parser parse comments and attach them to nodes, as
   * opposed to discarding them.
   */
  keepComments?: boolean
  /**
   * LangVariant describes a shell language variant to use when tokenizing and
   * parsing shell code. The zero value is [LangBash].
   */
  variant?: LangVariant
  /**
   * StopAt configures the lexer to stop at an arbitrary word, treating it as if
   * it were the end of the input. It can contain any characters except
   * whitespace, and cannot be over four bytes in size.
   *
   * This can be useful to embed shell code within another language, as one can
   * use a special word to mark the delimiters between the two.
   *
   * As a word, it will only apply when following whitespace or a separating
   * token. For example, StopAt("$$") will act on the inputs "foo $$" and
   * "foo;$$", but not on "foo '$$'".
   *
   * The match is done by prefix, so the example above will also act on "foo
   * $$bar".
   */
  stopAt?: string
  /**
   * RecoverErrors allows the parser to skip up to a maximum number of errors in
   * the given input on a best-effort basis. This can be useful to tab-complete
   * an interactive shell prompt, or when providing diagnostics on slightly
   * incomplete shell source.
   *
   * Currently, this only helps with mandatory tokens from the shell grammar
   * which are not present in the input. They result in position fields or nodes
   * whose position report [Pos.IsRecovered] as true.
   *
   * For example, given the input
   *
   *     (foo |
   *
   * The result will contain two recovered positions; first, the pipe requires a
   * statement to follow, and as [Stmt.Pos] reports, the entire node is
   * recovered. Second, the subshell needs to be closed, so [Subshell.Rparen] is
   * recovered.
   */
  recoverErrors?: number
  /**
   * KeepComments makes the parser parse comments and attach them to nodes, as
   * opposed to discarding them.
   *
   * @default true
   */
  keepComments: boolean
  /**
   * LangVariant describes a shell language variant to use when tokenizing and
   * parsing shell code. The zero value is [LangBash].
   */
  variant: LangVariant
  /**
   * StopAt configures the lexer to stop at an arbitrary word, treating it as if
   * it were the end of the input. It can contain any characters except
   * whitespace, and cannot be over four bytes in size.
   *
   * This can be useful to embed shell code within another language, as one can
   * use a special word to mark the delimiters between the two.
   *
   * As a word, it will only apply when following whitespace or a separating
   * token. For example, StopAt("$$") will act on the inputs "foo $$" and
   * "foo;$$", but not on "foo '$$'".
   *
   * The match is done by prefix, so the example above will also act on "foo
   * $$bar".
   */
  stopAt: string
  /**
   * RecoverErrors allows the parser to skip up to a maximum number of errors in
   * the given input on a best-effort basis. This can be useful to tab-complete
   * an interactive shell prompt, or when providing diagnostics on slightly
   * incomplete shell source.
   *
   * Currently, this only helps with mandatory tokens from the shell grammar
   * which are not present in the input. They result in position fields or nodes
   * whose position report [Pos.IsRecovered] as true.
   *
   * For example, given the input
   *
   *     (foo |
   *
   * The result will contain two recovered positions; first, the pipe requires a
   * statement to follow, and as [Stmt.Pos] reports, the entire node is
   * recovered. Second, the subshell needs to be closed, so [Subshell.Rparen] is
   * recovered.
   */
  recoverErrors: number

  // printer
  /**
   * Indent sets the number of spaces used for indentation. If set to 0, tabs
   * will be used instead.
   */
  indent: number
  /**
   * BinaryNextLine will make binary operators appear on the next line when a
   * binary command, such as a pipe, spans multiple lines. A backslash will be
   * used.
   *
   * @default true
   */
  binaryNextLine: boolean
  /**
   * SwitchCaseIndent will make switch cases be indented. As such, switch case
   * bodies will be two levels deeper than the switch itself.
   */
  switchCaseIndent: boolean
  /**
   * SpaceRedirects will put a space after most redirection operators. The
   * exceptions are '>&', '<&', '>(', and '<('.
   */
  spaceRedirects: boolean
  /**
   * KeepPadding will keep most nodes and tokens in the same column that they
   * were in the original source. This allows the user to decide how to align
   * and pad their code with spaces.
   *
   * Note that this feature is best-effort and will only keep the alignment
   * stable, so it may need some human help the first time it is run.
   *
   * @deprecated: this formatting option is flawed and buggy, and often does
   * not result in what the user wants when the code gets complex enough.
   *
   * The next major version, v4, will remove this feature entirely.
   * See: https://github.com/mvdan/sh/issues/658
   */
  keepPadding: boolean
  /**
   * Minify will print programs in a way to save the most bytes possible. For
   * example, indentation and comments are skipped, and extra whitespace is
   * avoided when possible.
   */
  minify: boolean
  /**
   * SingleLine will attempt to print programs in one line. For example, lists
   * of commands or nested blocks do not use newlines in this mode. Note that
   * some newlines must still appear, such as those following comments or around
   * here-documents.
   *
   * Print's trailing newline when given a [*File] is not affected by this
   * option.
   */
  singleLine: boolean
  /** FunctionNextLine will place a function's opening braces on the next line. */
  functionNextLine: boolean
}
```

More details on [godoc](https://godoc.org/mvdan.cc/sh/syntax#NewParser)

## Sponsors and Backers

[![Sponsors and Backers](https://raw.githubusercontent.com/1stG/static/master/sponsors.svg)](https://github.com/sponsors/JounQin)

### Sponsors

| 1stG                                                                                                                   | RxTS                                                                                                                   | UnTS                                                                                                                   |
| ---------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| [![1stG Open Collective sponsors](https://opencollective.com/1stG/organizations.svg)](https://opencollective.com/1stG) | [![RxTS Open Collective sponsors](https://opencollective.com/rxts/organizations.svg)](https://opencollective.com/rxts) | [![UnTS Open Collective sponsors](https://opencollective.com/unts/organizations.svg)](https://opencollective.com/unts) |

### Backers

| 1stG                                                                                                                | RxTS                                                                                                                | UnTS                                                                                                                |
| ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| [![1stG Open Collective backers](https://opencollective.com/1stG/individuals.svg)](https://opencollective.com/1stG) | [![RxTS Open Collective backers](https://opencollective.com/rxts/individuals.svg)](https://opencollective.com/rxts) | [![UnTS Open Collective backers](https://opencollective.com/unts/individuals.svg)](https://opencollective.com/unts) |

## Changelog

Detailed changes for each release are documented in [CHANGELOG.md](./CHANGELOG.md).

## License

[MIT][] © [JounQin][]@[1stG.me][]

[1stG.me]: https://www.1stG.me
[JounQin]: https://github.com/JounQin
[MIT]: http://opensource.org/licenses/MIT
[dockerfmt]: https://github.com/reteps/dockerfmt
[mvdan-sh]: https://github.com/mvdan/sh
[prettier]: https://prettier.io
[sh-syntax]: https://github.com/un-ts/sh-syntax
