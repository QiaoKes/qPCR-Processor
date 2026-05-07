# Quality Guidelines

> Code quality standards for backend development.

---

## Overview

<!--
Document your project's quality standards here.

Questions to answer:
- What patterns are forbidden?
- What linting rules do you enforce?
- What are your testing requirements?
- What code review standards apply?
-->

(To be filled by the team)

---

## Forbidden Patterns

<!-- Patterns that should never be used and why -->

(To be filled by the team)

---

## Required Patterns

<!-- Patterns that must always be used -->

(To be filled by the team)

---

## Testing Requirements

Bug fixes for data normalization must include regression tests that cover the
runtime types produced by file readers, not only the types shown in JSON config.

For sample mapping, Excel numeric sample names may arrive as `float` values
such as `1.0`, while JSON mapping keys are strings such as `"1"`. Mapping code
must normalize integral numeric values before lookup and tests must cover
`1.0`, `1`, and `"1"` matching the same config key.

---

## Code Review Checklist

When reviewing data processing changes:

* Check that values crossing file/config boundaries are normalized before
  comparison or dictionary lookup.
* Check that pandas columns receiving mixed string/numeric replacements are not
  left in a dtype that rejects the replacement under newer pandas versions.
* Check that unmapped values remain unchanged.
