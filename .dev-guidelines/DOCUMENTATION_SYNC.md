# Documentation Sync Rules

**Principle:** Code changes and documentation must remain synchronized. When implementing features or fixes, always evaluate whether public-facing docs need updates, and suggest improvements when they do.

## When to Check Documentation

Trigger these checks whenever you modify:
- **Feature code** (new capabilities, changed behavior)
- **Configuration files** (schemas, defaults, settings)
- **APIs** (endpoints, parameters, return values)
- **Installation/setup** (dependencies, scripts, systemd services)
- **File formats** or **data structures**
- **Error handling** or **troubleshooting paths**

## Documentation Evaluation Checklist

For each code change, scan these files:

| File | Check | Examples |
|------|-------|----------|
| `INSTALLATION.md` | Is new setup required? New packages? Changed installer logic? | New systemd service; pyenv version bump; new Python dependency |
| `USER_GUIDE.md` | Does user-facing behavior change? New settings? | Camera rotation; WiFi SSID format; file share naming |
| `TROUBLESHOOTING.md` | Are failure modes affected? New error conditions? | SMB delete permissions; file sync issues; temp directory locations |
| `ARCHITECTURE.md` | Did core structure change? New subsystem? | Settings manager rewrite; new Publisher type |
| `README.md` | Release notes or known issues needing updates? | Release checklist; smoke test commands |
| `SMB_FILE_SHARING.md` | Changes to file publish, permissions, or sharing? | SMB alias names; permission model; empty share behavior |

## Update Suggestions

When code changes should trigger doc updates, **always suggest the changes explicitly**. Format:

```
### Suggested doc update: TROUBLESHOOTING.md

**Section:** "File Delete Permission Denied" (new section)
**Reason:** New _ensure_smb_permissions() call means guest users can now delete files if pi:pi ownership is set.

**Proposed text:**
"If you cannot delete shared files over SMB as guest user:
1. Check file ownership: `ls -l /home/pi/shared/` should show pi:pi
2. Check service running: `systemctl status camcontroller.service`
3. Restart service to re-heal permissions: `sudo systemctl restart camcontroller.service`"
```

## Swedish Document Pairs

If a `.md` document has a `_*_swe.md` sibling (e.g., `USER_GUIDE_SWE.md` pairs with `USER_GUIDE.md`):

- **Translate code-driven changes** to the Swedish version in the same PR
- Apply the same logic/structure to both docs
- For example, if you add a new camera tip to `USER_GUIDE.md`, add equivalent text to `USER_GUIDE_SWE.md` in Swedish

See [SWEDISH_TRANSLATIONS.md](SWEDISH_TRANSLATIONS.md) for detailed translation guidelines.

## Documentation-Driven Development

For larger features, consider writing documentation first:
1. Draft user guide section describing the feature
2. Add troubleshooting entry for common issues
3. Update INSTALLATION.md if needed
4. Then implement code to match the documented behavior

This prevents "code now, document later" gaps.
