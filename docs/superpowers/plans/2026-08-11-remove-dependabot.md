# Dependabot Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove repository-managed Dependabot update PR generation while leaving application dependencies and GitHub repository security-alert settings unchanged.

**Architecture:** Delete the only repository-level Dependabot configuration file. Verify that no product or dependency-lock files change and that the existing CI suite remains green.

**Tech Stack:** GitHub Dependabot configuration, Git, GitHub Actions

## Global Constraints

- Do not modify `uv.lock`, Dockerfiles, application code, or CI/CD workflows.
- Do not change GitHub repository security-alert settings.
- Keep the removal in its own commit.

---

### Task 1: Remove the Dependabot configuration

**Files:**
- Delete: `.github/dependabot.yml`

**Interfaces:**
- Consumes: GitHub's repository-level Dependabot configuration discovery.
- Produces: No `.github/dependabot.yml`, so repository-configured version update jobs are absent.

- [ ] **Step 1: Delete the configuration**

Delete `.github/dependabot.yml` and do not edit any dependency or workflow files.

- [ ] **Step 2: Verify the focused diff**

Run: `git diff --name-status main...HEAD` and `git diff --check`

Expected: the feature diff contains the Dependabot configuration removal plus the approved design and implementation documents, with no whitespace errors.

- [ ] **Step 3: Run local checks**

Run: `.venv\\Scripts\\pytest.exe -p no:cacheprovider` and `.venv\\Scripts\\ruff.exe check .`

Expected: all tests and lint checks pass.

- [ ] **Step 4: Commit the removal**

```powershell
git add .github/dependabot.yml
git commit -m "chore: remove Dependabot configuration"
```

- [ ] **Step 5: Push and verify PR CI**

Run: `git push` and monitor PR #56.

Expected: Python tests, deployment assets, and Compose smoke test all pass.
