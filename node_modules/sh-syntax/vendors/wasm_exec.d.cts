import _fs from 'node:fs'

declare global {
  namespace globalThis {
    var fs: typeof _fs
  }
}
