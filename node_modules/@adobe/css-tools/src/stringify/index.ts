import type { CssStylesheetAST } from '../type';
import Compiler, { type CompilerOptions } from './compiler';

export default (node: CssStylesheetAST, options?: CompilerOptions) => {
  const compiler = new Compiler(options || {});
  return compiler.compile(node);
};
