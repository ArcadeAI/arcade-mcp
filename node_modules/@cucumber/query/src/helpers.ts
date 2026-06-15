import { TestStepResultStatus } from '@cucumber/messages'

export function statusOrdinal(status: TestStepResultStatus) {
  return [
    TestStepResultStatus.UNKNOWN,
    TestStepResultStatus.PASSED,
    TestStepResultStatus.SKIPPED,
    TestStepResultStatus.PENDING,
    TestStepResultStatus.UNDEFINED,
    TestStepResultStatus.AMBIGUOUS,
    TestStepResultStatus.FAILED,
  ].indexOf(status)
}

export const assert = {
  ok(target: unknown, message: string) {
    if (!target) {
      throw new Error(message)
    }
  },
}
