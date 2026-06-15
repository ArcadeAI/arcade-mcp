# watskeburt

Get changed files & their statuses since any git _revision_

## :construction_worker: usage

### :scroll: API

```javascript
import { list, getSHA } from "watskeburt";

// print the SHA1 of the current HEAD
console.log(await getSHA());

// list all files that differ between 'main' and the current revision (including
// files not staged for commit and files not under revision control)
/** @type {import('watskeburt').IChange[]} */
const lChangedFiles = await list({ oldRevision: "main" });

// list all files that differ between 'v0.6.1' and 'v0.7.1' (by definition
// won't include files staged for commit and/ or not under revision control)
/** @type {import('watskeburt').IChange[]} */
const lChangedFiles = await list({
  oldRevision: "v0.6.1",
  newRevision: "v0.7.1",
});

// list all files that differ between 'main' and the current revision
// (excluding files not staged for commit)
/** @type {import('watskeburt').IChange[]|string} */
const lChangedFiles = await list({
  oldRevision: "main",
  trackedOnly: false, // when set to true leaves out files not under revision control
  outputType: "json", // options: "object", "json" and "regex"
});
```

The array of changes this returns looks like this:

```javascript
[
  {
    name: "doc/cli.md",
    type: "modified",
  },
  {
    name: "test/thing.spec.mjs",
    type: "renamed",
    oldName: "test/old-thing.spec.mjs",
  },
  {
    name: "src/not-tracked-yet.mjs",
    type: "untracked",
  },
];
```

### :shell: cli

Works with node >=18.11

```shell
# list all JavaScript-ish files changed since main in a regular expression
$ npx watskeburt main
^(src/cli[.]mjs|src/formatters/regex[.]mjs|src/version[.]mjs)$
```

This emits a regex that contains all changed files that could be
source files in the JavaScript ecosystem (.js, .mjs, .ts, .tsx ...). It can
be used in e.g. dependency-cruiser's `--focus` and `--reaches` filters.

The JSON output (= the array above, serialized) also contains all other
extensions.

```
Usage: watskeburt [options] [old-revision] [new-revision]

lists files & their statuses since [old-revision] or between [old-revision] and [new-revision].

-> When you don't pass a revision old-revision defaults to the current one.

Options:
  -T, --outputType <type>  what format to emit (choices: "json", "regex", default: "regex")
  --trackedOnly            only take tracked files into account (default: false)
  -V, --version            output the version number
  -e, --extensions <list>  comma separated list of file extensions to consider
                           - pass "*" to consider all extensions
                           - currently applicable only to the "regex" reporter
                           - defaults to to most popular extensions in the
                             JavaScript/ TypeScript ecosystem
  -h, --help               display help for command
```

Default list of extensions (cli, regex reporter only):
`"cjs, cjsx, coffee, csx, cts, js, json, jsx, litcoffee, ls, mjs, mts, svelte, ts, tsx, vue, vuex"`.

## why?

I needed something robust to support caching in
[dependency-cruiser](https://github.com/sverweij/dependency-cruiser) and to
run standalone to use _in combination_ with dependency-cruiser.

A few specialized packages like this existed, but they had fallen out of
maintenance. More generic packages still were maintained, but for my use
case they were overkill.

## 🇳🇱 what does 'watskeburt' mean?

Wazzup.

_watskeburt_ is a fast pronunciation of the Dutch "wat is er gebeurd?"
(_what has happened?_) or "wat er is gebeurd" (_what has happened_).
