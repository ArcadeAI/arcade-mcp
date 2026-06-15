# `@reteps/dockerfmt`

Bindings around the Golang `dockerfmt` tooling. It compiles the Go code to WebAssembly (using standard Go's `GOOS=js GOARCH=wasm` target), which is then used in the JS bindings.


```js
import { formatDockerfile } from '@reteps/dockerfmt'
// Alternatively, you can use `formatDockerfileContents` to format a string instead of a file.

const result = await formatDockerfile('../tests/comment.dockerfile', { indent: 4, trailingNewline: true })

console.log(result)
```
