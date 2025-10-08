# OodaTools Project Instructions

## File Organization

### `/Local` Directory Convention
**All non-deployment files must be stored in `/Local` directory:**

- **Test files**: All test scripts, test data, test configurations
- **Markdown documentation**: Development notes, investigation files, research docs
- **Temporary files**: Debug scripts, experimental code, scratch files
- **Development artifacts**: Any files not intended for production deployment

**Purpose**: Keep the root directory clean and deployment-ready by isolating development/testing artifacts.

**Examples of files that belong in `/Local`:**
- `test_*.py` - Test scripts
- `debug_*.py` - Debug utilities
- `*.md` (except README.md) - Development documentation
- Experimental or temporary code files
- Screenshots and debug images
- Investigation and analysis files

**Git Ignore**: Ensure `/Local` is added to `.gitignore` to prevent accidental commits to GitHub.
