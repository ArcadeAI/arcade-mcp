# Review rubric

Each finding has a severity, a location, an explanation, and the evidence you used.

P0. The change loses data, crosses a security boundary, or cannot be built.

P1. The change is wrong, regresses existing behavior, or leaves a required behavior untested.

P2. The change will mislead the next editor and does not change current behavior.

P3. A note the author can leave for later.

A policy with `failOn: P1` fails the review when any finding is P0 or P1. P2 and P3 do not fail that policy.
