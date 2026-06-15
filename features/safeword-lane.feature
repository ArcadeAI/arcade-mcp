Feature: Safeword BDD lane

  The acceptance lane safeword scaffolds: plain-English scenarios in
  `features/`, TypeScript step definitions in `steps/`. Replace this starter
  with your own features — `safeword codify --format gherkin <ticket>`
  generates them from a ticket's test-definitions.md.

  Scenario: the lane is wired
    When I run shell command "node --version"
    Then the shell exit code is 0
    And the shell output contains "v"
