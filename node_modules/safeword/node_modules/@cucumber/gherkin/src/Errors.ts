import type * as messages from '@cucumber/messages'

export class GherkinException extends Error {
  public errors: Error[]
  public location: messages.Location

  constructor(message: string) {
    super(message)

    const actualProto = new.target.prototype

    // https://stackoverflow.com/questions/41102060/typescript-extending-error-class
    if (Object.setPrototypeOf) {
      Object.setPrototypeOf(this, actualProto)
    } else {
      // @ts-expect-error
      this.__proto__ = actualProto
    }
  }

  protected static _create(message: string, location?: messages.Location) {
    const column = location != null ? location.column || 0 : -1
    const line = location != null ? location.line || 0 : -1
    const m = `(${line}:${column}): ${message}`
    // biome-ignore lint/complexity/noThisInStatic: subclasses rely on `this` resolving to the calling constructor
    const err = new this(m)
    err.location = location
    return err
  }
}

export class ParserException extends GherkinException {
  public static create(message: string, line: number, column: number) {
    const err = new ParserException(`(${line}:${column}): ${message}`)
    err.location = { line, column }
    return err
  }
}

export class CompositeParserException extends GherkinException {
  public static create(errors: Error[]) {
    const message = `Parser errors:\n${errors.map((e) => e.message).join('\n')}`
    const err = new CompositeParserException(message)
    err.errors = errors
    return err
  }
}

export class AstBuilderException extends GherkinException {
  public static create(message: string, location: messages.Location) {
    return AstBuilderException._create(message, location)
  }
}

export class NoSuchLanguageException extends GherkinException {
  public static create(language: string, location?: messages.Location) {
    const message = `Language not supported: ${language}`
    return NoSuchLanguageException._create(message, location)
  }
}
