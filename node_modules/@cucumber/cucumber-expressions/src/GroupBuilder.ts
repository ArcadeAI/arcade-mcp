import type { RegExpExecArray } from 'regexp-match-indices'

import Group from './Group.js'

export default class GroupBuilder {
  public source: string
  public capturing = true
  private readonly groupBuilders: GroupBuilder[] = []

  public add(groupBuilder: GroupBuilder) {
    this.groupBuilders.push(groupBuilder)
  }

  public build(match: RegExpExecArray, nextGroupIndex: () => number): Group {
    const groupIndex = nextGroupIndex()
    const children = this.groupBuilders.map((gb) => gb.build(match, nextGroupIndex))
    const value = match[groupIndex]
    const index = match.indices[groupIndex]
    const start = index ? index[0] : undefined
    const end = index ? index[1] : undefined
    return new Group(value, start, end, children.length === 0 ? undefined : children)
  }

  public setNonCapturing() {
    this.capturing = false
  }

  get children() {
    return this.groupBuilders
  }

  public moveChildrenTo(groupBuilder: GroupBuilder) {
    for (const child of this.groupBuilders) {
      groupBuilder.add(child)
    }
  }
}
