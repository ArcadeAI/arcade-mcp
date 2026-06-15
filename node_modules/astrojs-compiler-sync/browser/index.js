let waitSetupForAstroCompilerWasm;

function getService() {
  return globalThis["@astrojs/compiler"] || setup();
}

/**
 * Parse code by `@astrojs/compiler`
 */
export function parse(code, options) {
  const service = getService();
  if (typeof service.then === "function") {
    return service.then(() => parse(code, options));
  }
  const { ast, ...other } = getService().parse(code, options);
  return { ...other, ast: JSON.parse(ast) };
}

/** setup */
export function setup(astroVersion) {
  return (
    waitSetupForAstroCompilerWasm ||
    (waitSetupForAstroCompilerWasm = setupImpl(astroVersion))
  );
}

async function genAstroWasmUrl(astroVersion) {
  const rootUrl = `https://unpkg.com/@astrojs/compiler${
    astroVersion ? `@${astroVersion}` : ""
  }`;
  const packageJsonUrl = `${rootUrl}/package.json`;

  // eslint-disable-next-line n/no-unsupported-features/node-builtins -- on browser
  const pkg = await fetch(packageJsonUrl).then((response) => response.json());

  if (pkg.exports && pkg.exports["./astro.wasm"]) {
    return new URL(pkg.exports["./astro.wasm"], packageJsonUrl).toString();
  }

  return "https://unpkg.com/browse/@astrojs/compiler/dist/astro.wasm";
}

async function setupImpl(astroVersion) {
  const [{ default: Go }, wasmBuffer] = await Promise.all([
    import("./wasm_exec.js"),
    genAstroWasmUrl(astroVersion)
      // eslint-disable-next-line n/no-unsupported-features/node-builtins -- on browser
      .then((url) => fetch(url))
      .then((response) => response.arrayBuffer()),
  ]);

  const go = new Go();
  try {
    const mod = await WebAssembly.compile(wasmBuffer);
    const instance = await WebAssembly.instantiate(mod, go.importObject);
    go.run(instance);

    return watch();
  } catch (e) {
    // eslint-disable-next-line no-console -- log
    console.log(e);
    throw e;
  }

  function watch() {
    return new Promise((resolve) => {
      if (globalThis["@astrojs/compiler"]) {
        resolve(globalThis["@astrojs/compiler"]);
      } else {
        setTimeout(() => {
          resolve(watch());
        }, 100);
      }
    });
  }
}
