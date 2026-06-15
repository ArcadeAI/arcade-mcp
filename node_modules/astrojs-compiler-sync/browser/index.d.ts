import type * as compiler from "@astrojs/compiler";

export function parse(
  ...args: Parameters<typeof compiler.parse>
): Awaited<ReturnType<typeof compiler.parse>>;
export function setup(astroVersion: string): Promise<typeof compiler>;
