# Git Workflow & Release Process

**Principle:** Clean commit history, clear messages, and coordinated releases prevent confusion and make debugging easier. All changes flow through main with discipline.

## Branch Strategy

This project uses **trunk-based development** (main only for releases).

### Rules

1. **Always work on `main`** (no long-lived feature branches)
2. **Keep commits small and focused** (one feature/fix per commit where possible)
3. **Rebase before pushing** to keep history clean
4. **Never force-push** to `main`
5. **Tag releases** on `main` with version numbers

## Commit Message Format

```
<type>: <subject> [<scope>]

<body>

<footer>
```

### Types

- `feat:` New feature or capability
- `fix:` Bug fix
- `docs:` Documentation changes (INSTALLATION.md, USER_GUIDE.md, etc.)
- `refactor:` Code restructuring (no behavior change)
- `test:` New or updated tests
- `chore:` Tooling, build scripts, environment setup
- `perf:` Performance improvement

### Subject Line

- Imperative mood ("add", "fix", "update" — not "added", "fixed", "updated")
- No period at end
- Max 50 characters
- Lowercase first letter
- Include scope if helpful: `docs(installation): add camera module 2 prerequisites`

### Body (optional but recommended)

- Explain *why* the change was made
- Link to related issues: `Fixes #123` or `Related to #456`
- Reference affected subsystems: "FilePublisher, SMB permissions"
- Note any breaking changes: `BREAKING: Settings schema format changed from JSON to YAML`

### Footer

```
Co-authored-by: <Name> <email>
Reviewed-by: <Name> <email>
```

### Examples

```
fix: correct SMB guest delete permission issue

The service runs as root, creating files with root:root ownership.
Guest users mapped to pi cannot delete root-owned files over SMB.

Solution: Call _ensure_smb_permissions() after publish() and run
startup healing script via camcontroller.service ExecStartPre.

Fixes #45
Related-to: SMB_FILE_SHARING.md update
```

```
docs: update USER_GUIDE to reflect new WiFi SSID format

Added clarification that SSID defaults to "CamController-<SERIAL>".
Updated Swedish translation (USER_GUIDE_SWE.md).
Regenerated PDFs for both languages.

Reviewed-by: Jane User <jane@example.com>
```

```
feat: add atomic writes for settings to prevent power-cut corruption

Settings manager now writes to temp file, calls fsync, then atomically
renames to final path. Parent directory fsync also performed.

This prevents settings corruption if power is lost mid-write.

Changelog entry added to README.md release notes.
```

## Before Pushing

1. **Verify tests pass** (see CODE_QUALITY.md)
2. **Check documentation** (see DOCUMENTATION_SYNC.md)
3. **Review your own commits** (`git log main..HEAD`)
4. **Rebase if needed** (`git rebase -i main`)

```bash
# See what you're about to push
git log main..HEAD --oneline

# Interactive rebase to squash or reorder commits (optional)
git rebase -i main

# Final push
git push origin main
```

## Version Numbers

Follow **Semantic Versioning** (MAJOR.MINOR.PATCH):

- `MAJOR`: Incompatible API changes or major feature additions
- `MINOR`: New features, backwards-compatible
- `PATCH`: Bug fixes, documentation, minor improvements

Examples:
- `1.0.0` — First release
- `1.1.0` — New camera model support
- `1.1.1` — SMB permission bug fix
- `2.0.0` — Complete rewrite of settings system (breaking change)

## Release Process

### Before Release Day

1. **Update VERSION file** at project root with new version
2. **Update RELEASE_NOTES.md** with:
   - New version number
   - List of features added
   - List of bugs fixed
   - Any breaking changes
   - Installation/upgrade notes if applicable
3. **Run full smoke test suite** (see SMOKE_TESTS.md checklist in README.md)
4. **Verify documentation is current:**
   - INSTALLATION.md ← New dependencies?
   - TROUBLESHOOTING.md ← New error scenarios?
   - USER_GUIDE.md (EN + SWE) ← Behavior changes?
5. **Regenerate PDFs** if guide was updated:
   ```bash
   .venv/bin/python scripts/generate_pdfs.py
   ```
6. **Commit release prep:**
   ```bash
   git add VERSION RELEASE_NOTES.md USER_GUIDE*.md USER_GUIDE*.pdf
   git commit -m "chore: prepare v1.2.3 release

   - Updated VERSION, RELEASE_NOTES, user guides
   - All tests passing
   - Ready for release tag"
   ```

### Release Day

1. **Create release tag:**
   ```bash
   git tag -a v1.2.3 -m "Release version 1.2.3"
   ```
2. **Push changes and tag:**
   ```bash
   git push origin main --tags
   ```
3. **Build distribution packages** (if applicable):
   ```bash
   cd build-scripts
   python release_manager.py prepare 1.2.3
   ```
4. **Archive release notes** (optional):
   ```bash
   cp RELEASE_NOTES.md releases/v1.2.3-RELEASE_NOTES.md
   ```

## File Organization for Releases

```
releases/
  v1.2.3/
    PyRpiCamController-1.2.3.tar.gz
    checksums.txt
    RELEASE_NOTES.md
build-scripts/
  release_manager.py
  test_package.py
VERSION
RELEASE_NOTES.md
```

## Rollback Procedure

If a release has critical bugs:

1. **Identify the last good version TAG:**
   ```bash
   git describe --tags
   ```
2. **Create hotfix branch from tag:**
   ```bash
   git checkout -b hotfix/version -b <good-tag>
   ```
3. **Fix the issue** and test
4. **Commit with clear message:**
   ```bash
   git commit -m "fix: critical SMB regression in v1.2.3

   Fixes #999 - SMB share unreachable after v1.2.3 update
   
   Regression was introduced in commit abc123.
   Reverted _ensure_smb_permissions() to v1.2.2 behavior
   pending better solution for next release."
   ```
5. **Tag hotfix and push:**
   ```bash
   git tag -a v1.2.4 -m "Hotfix for critical SMB issue in v1.2.3"
   git push origin hotfix/version main --tags
   ```

## Helpful Git Commands

```bash
# See all tags and versions
git tag --list

# See commits since last release
git log v1.2.2..v1.2.3 --oneline

# Check what files changed
git diff v1.2.2 v1.2.3 --name-only

# Ammend last commit (before pushing)
git add .
git commit --amend

# Undo unpushed commit (keep changes)
git reset --soft HEAD~1

# Undo unpushed commit (discard changes)
git reset --hard HEAD~1
```

## Related Files

- `VERSION` — Current version number
- `RELEASE_NOTES.md` — User-facing change summary
- `ARCHITECTURE.md` — Technical documentation (update if structure changes)
- `README.md` — Release readiness checklist and smoke test commands
- `build-scripts/release_manager.py` — Automated release packaging
