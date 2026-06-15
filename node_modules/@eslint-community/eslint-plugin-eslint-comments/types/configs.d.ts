import type { Linter } from "eslint"

declare namespace Configs {
    import defaultExports = Configs

    export const recommended: Linter.FlatConfig

    export { defaultExports as default }
}

export = Configs
