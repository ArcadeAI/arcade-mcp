import fs from 'node:fs'
import path from 'node:path'
import { type Readable, Transform, type TransformCallback } from 'node:stream'
import type { Envelope } from '@cucumber/messages'

export class CucumberHtmlStream extends Transform {
  private template: string | null = null
  private preMessageWritten = false
  private postMessageWritten = false
  private firstMessageWritten = false

  /**
   * @param cssPath
   * @param jsPath
   * @param iconPath
   */
  constructor(
    private readonly cssPath: string = path.join(__dirname, '..', 'main.css'),
    private readonly jsPath: string = path.join(__dirname, '..', 'main.js'),
    private readonly iconPath: string = path.join(__dirname, 'icon.url')
  ) {
    super({ objectMode: true })
  }

  public _transform(envelope: Envelope, _encoding: string, callback: TransformCallback): void {
    if (this.postMessageWritten) {
      callback(new Error('Stream closed'))
      return
    }

    this.writePreMessageUnlessAlreadyWritten((err) => {
      if (err) {
        callback(err)
        return
      }
      this.writeMessage(envelope)
      callback()
    })
  }

  public _flush(callback: TransformCallback): void {
    this.writePostMessage(callback)
  }

  private writePreMessageUnlessAlreadyWritten(callback: TransformCallback) {
    if (this.preMessageWritten) {
      return callback()
    }
    this.preMessageWritten = true
    this.writeTemplateBetween(null, '{{title}}', (err) => {
      if (err) return callback(err)
      this.push('Cucumber')
      this.writeTemplateBetween('{{title}}', '{{icon}}', (err) => {
        if (err) return callback(err)
        this.writeFile(this.iconPath, (err) => {
          if (err) return callback(err)
          this.writeTemplateBetween('{{icon}}', '{{css}}', (err) => {
            if (err) return callback(err)
            this.writeFile(this.cssPath, (err) => {
              if (err) return callback(err)
              this.writeTemplateBetween('{{css}}', '{{custom_css}}', (err) => {
                if (err) return callback(err)
                this.writeTemplateBetween('{{custom_css}}', '{{messages}}', (err) => {
                  if (err) return callback(err)
                  callback()
                })
              })
            })
          })
        })
      })
    })
  }

  private writePostMessage(callback: TransformCallback) {
    this.writePreMessageUnlessAlreadyWritten((err) => {
      if (err) return callback(err)
      this.writeTemplateBetween('{{messages}}', '{{script}}', (err) => {
        if (err) return callback(err)
        this.writeFile(this.jsPath, (err) => {
          if (err) return callback(err)
          this.writeTemplateBetween('{{script}}', '{{custom_script}}', (err) => {
            if (err) return callback(err)
            this.writeTemplateBetween('{{custom_script}}', null, callback)
          })
        })
      })
    })
  }

  private writeFile(path: string, callback: (error?: Error | null) => void) {
    const cssStream: Readable = fs.createReadStream(path, { encoding: 'utf-8' })
    cssStream.on('data', (chunk) => this.push(chunk))
    cssStream.on('error', (err) => callback(err))
    cssStream.on('end', callback)
  }

  private writeTemplateBetween(
    begin: string | null,
    end: string | null,
    callback: (err?: Error | null) => void
  ) {
    this.readTemplate((err, template) => {
      if (err) return callback(err)
      if (!template) return callback(new Error('template is required if error is missing'))
      const beginIndex = begin == null ? 0 : template.indexOf(begin) + begin.length
      const endIndex = end == null ? template.length : template.indexOf(end)
      this.push(template.substring(beginIndex, endIndex))
      callback()
    })
  }

  private readTemplate(callback: (error?: Error | null, data?: string) => void) {
    if (this.template !== null) {
      return callback(null, this.template)
    }
    fs.readFile(`${__dirname}/index.mustache`, { encoding: 'utf-8' }, (err, template) => {
      if (err) return callback(err)
      this.template = template
      return callback(null, template)
    })
  }

  private writeMessage(envelope: Envelope) {
    if (!this.firstMessageWritten) {
      this.firstMessageWritten = true
    } else {
      this.push(',')
    }
    // Replace < with \x3C
    // https://html.spec.whatwg.org/multipage/scripting.html#restrictions-for-contents-of-script-elements
    this.push(JSON.stringify(envelope).replace(/</g, '\\x3C'))
  }
}
