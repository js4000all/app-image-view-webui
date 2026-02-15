# AGENT_RULES.md

## Purpose

This document defines strict rules for AI agents (Codex, etc.) when creating Pull Requests in this repository.

The primary goals are:

* Maintain reviewability
* Ensure safety of changes
* Preserve clear intent per PR
* Minimize regression risk
* Enable fast and reliable merging

These rules are mandatory.

---

## Core Principle: Single Responsibility Per Pull Request

Each Pull Request MUST have exactly one intent.

Never mix multiple intents in a single PR.

Allowed intents (choose exactly one):

* behavior: feature addition or bug fix
* refactor: structure change without behavior change
* test: test addition or improvement only
* infra: CI, build, lint, config, tooling only
* docs: documentation only
* chore: dependency updates or maintenance only

Forbidden combinations (examples):

* refactor + behavior
* refactor + infra
* behavior + infra
* migration + refactor
* behavior + docs (docs must be separate)

If multiple changes are needed, create multiple PRs.

---

## PR Title Format (Mandatory)

Format:

<type>: <short description>

Examples:

feat: add session caching
fix: handle null pointer in auth middleware
refactor: split UserService into smaller modules
test: add unit tests for UserRepository
infra: add typecheck step to CI
docs: document authentication flow
chore: update dependencies

Allowed types:

* feat
* fix
* refactor
* test
* infra
* docs
* chore

---

## Refactor Rules (Strict)

Refactor PRs MUST NOT:

* Change behavior
* Change business logic
* Change public API contracts
* Add features
* Remove features

Refactor PRs MUST:

* Preserve behavior exactly
* Pass all existing tests without modification
* Only improve structure, readability, or maintainability

If behavior change is required, create a separate PR.

---

## Behavior Change Rules

Behavior PRs MUST:

* Be minimal and focused
* Only implement the specific feature or fix
* Avoid unrelated refactoring
* Avoid formatting-only changes

If refactoring is needed first, create a refactor PR before behavior PR.

---

## Test Rules

Test PRs MUST:

* Only add or improve tests
* NOT change production behavior
* NOT refactor production code (unless strictly necessary)

---

## Infra Rules

Infra PRs include only:

* GitHub Actions
* CI/CD
* lint configuration
* build configuration
* tooling setup

Infra PRs MUST NOT change application logic.

---

## Documentation Rules

Docs PRs MUST:

* Only modify documentation
* NOT change code behavior
* NOT include refactoring

---

## PR Size Guidelines

Preferred size:

* Under 300 lines changed
* Ideal: under 150 lines

If change is larger, split into multiple PRs.

---

## Safety Requirements

All PRs MUST:

* Pass CI
* Pass typecheck
* Pass lint
* Pass tests
* Build successfully

Never bypass failing checks.

---

## Separation Strategy

If a task requires multiple change types, use this order:

1. refactor PR
2. test PR (if needed)
3. behavior PR
4. docs PR

Never combine them.

---

## Forbidden Actions

Never:

* Mix unrelated changes
* Modify large areas unnecessarily
* Rewrite entire files without reason
* Introduce hidden behavior changes in refactor PRs

---

## Preferred Strategy

When unsure, create smaller, safer, isolated PRs.

More small PRs are always preferred over fewer large PRs.

---

## Summary

One PR = One intent
Small, isolated, safe changes only.

