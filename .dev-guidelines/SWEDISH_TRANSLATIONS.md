# Swedish Translation Guidelines

**Principle:** Documents with `_swe` siblings must be kept in sync. When one is updated, the other should be translated to maintain feature parity across languages.

## Document Pairs

Current Swedish pairs:
- `USER_GUIDE.md` ↔ `USER_GUIDE_SWE.md` (end-user instructions)

Potential future pairs:
- `INSTALLATION.md` ↔ `INSTALLATION_SWE.md`
- `TROUBLESHOOTING.md` ↔ `TROUBLESHOOTING_SWE.md`

## When to Translate

**After modifying any base document** (e.g., `USER_GUIDE.md`):
1. Check if a `_swe` sibling exists
2. If yes, apply the same changes to the Swedish version
3. Use consistent Swedish terminology (see **Terminology** below)
4. Commit both files in the same PR

**Do not skip translation** — out-of-sync language versions cause user confusion.

## Translation Process

### 1. Identify Changes
Use `git diff` to see what changed in the base doc:
```bash
git diff USER_GUIDE.md
```

### 2. Apply Same Changes to Swedish Version
- Match structure (headings, sections, bullet points)
- Translate added/modified text to Swedish
- Preserve code blocks, file paths, and command examples (no translation needed)
- Keep formatting (bold, emphasis, links) identical

### 3. Review for Consistency
- Scan both versions side-by-side
- Ensure terminology matches previous sections
- Check that Swedish text reads naturally (not word-for-word translation of awkward English)

### 4. Commit Together
```bash
git add USER_GUIDE.md USER_GUIDE_SWE.md
git commit -m "Update user guide: add WiFi troubleshooting section (EN + SWE)"
```

## Swedish Terminology

Use these standardized terms consistently across all Swedish documents:

| English | Swedish | Context |
|---------|---------|---------|
| Camera | Kamera | General |
| WiFi | WiFi (no translation) | Networking |
| Settings / Configuration | Inställningar | UI/menus |
| Shared folder / File share | Delad mapp | SMB/network storage |
| Guest user | Gästanvändare | SMB permissions |
| Permissions / Rights | Behörigheter / Rättigheter | File system |
| Ownership | Ägare | File system |
| Service / Daemon | Tjänst | systemd |
| Log | Logg | System output |
| Troubleshooting | Felsökning | Support docs |
| SSH / Command line | SSH / Kommandorad | Remote access |
| SSID | SSID (no translation) | WiFi network name |
| Ethernet | Ethernet (no translation) | Network interface |
| Resolution | Upplösning | Camera settings |
| Frame rate | Bildhastighet / FPS | Camera settings |
| Zoom | Zoom (no translation) | Camera settings |

## Translation Tools

For future translations (if creating new `_swe` pairs):

1. **Manual translation** (preferred for technical docs):
   - Ensures accuracy and style consistency
   - Required for updates to existing docs

2. **AI translation review**:
   - Use as a starting point for new documents
   - Always review and edit manually for accuracy
   - Verify technical terms against the terminology table

3. **Keep glossary updated**:
   - Add new terms to the terminology table above
   - Discuss with Swedish-speaking testers before committing

## PDF Generation

When regenerating PDFs:
- Both `USER_GUIDE.md` and `USER_GUIDE_SWE.md` should generate up-to-date PDFs
- Use the WeasyPrint tool with consistent CSS styling
- Verify images are embedded correctly in both versions

Example commands:
```bash
# Generate English PDF
.venv/bin/python -c "
from pathlib import Path
import markdown
from weasyprint import HTML

project = Path('/home/psk/Dropbox/dev/PyRpiCamController')
md_text = (project / 'USER_GUIDE.md').read_text(encoding='utf-8')
html_body = markdown.markdown(md_text, extensions=['extra', 'sane_lists', 'tables', 'toc'])
# [HTML template and style...]
HTML(string=html_doc, base_url=str(project)).write_pdf(str(project / 'USER_GUIDE.pdf'))
"

# Generate Swedish PDF
.venv/bin/python -c "
from pathlib import Path
import markdown
from weasyprint import HTML

project = Path('/home/psk/Dropbox/dev/PyRpiCamController')
md_text = (project / 'USER_GUIDE_SWE.md').read_text(encoding='utf-8')
# [Same process, but read _SWE file, write _SWE PDF...]
"
```

## Quality Checklist

Before committing Swedish translations:
- ✅ All changes from base document are present in Swedish version
- ✅ Swedish text reads naturally (not robotic)
- ✅ Technical terms match the terminology table
- ✅ Links and code blocks are identical in both versions
- ✅ File paths and command examples are unchanged
- ✅ Both versions have the same heading structure
- ✅ No English text accidentally left in Swedish version
