# Release Process

This document describes how to create a new release for the BMW Wallbox integration.

## Overview

Releases are used to:
- Tag stable versions of the integration
- Notify HACS users of updates
- Track changes over time
- Provide downloadable versions

## Prerequisites

- All changes committed and pushed to `main` branch
- All tests passing (GitHub Actions green)
- CHANGELOG.md updated with changes
- Version number decided (following Semantic Versioning)

## Semantic Versioning

We follow [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.x.x): Breaking changes, incompatible API changes
- **MINOR** (x.1.x): New features, backwards compatible
- **PATCH** (x.x.1): Bug fixes, backwards compatible

Examples:
- `1.0.0` → `1.0.1`: Bug fix
- `1.0.0` → `1.1.0`: New feature (e.g., new sensor)
- `1.0.0` → `2.0.0`: Breaking change (e.g., renamed entities)

## Step-by-Step Release Process

### 1. Update Version Numbers

Update the version in `manifest.json`:

```bash
cd /Users/joaobelo/Git/Belo/wallbox
```

Edit `custom_components/bmw_wallbox/manifest.json`:
```json
{
  "domain": "bmw_wallbox",
  "name": "BMW Wallbox (OCPP)",
  "version": "1.1.0",  ← Update this
  ...
}
```

### 2. Update CHANGELOG.md

Add a new section at the top of `CHANGELOG.md`:

```markdown
## [1.1.0] - 2024-12-08

### Added
- New feature X
- New sensor Y

### Fixed
- Bug fix Z

### Changed
- Improved performance of ABC

[1.1.0]: https://github.com/JoaoPedroBelo/bmw-wallbox-ha/releases/tag/v1.1.0
```

### 3. Commit Version Changes

```bash
git add custom_components/bmw_wallbox/manifest.json CHANGELOG.md
git commit -m "Bump version to 1.1.0"
git push origin main
```

### 4. Wait for CI/CD

Wait for GitHub Actions to complete:
- Go to: https://github.com/JoaoPedroBelo/bmw-wallbox-ha/actions
- Ensure all checks pass ✅

### 5. Create and Push Git Tag

```bash
# Create annotated tag
git tag -a v1.1.0 -m "Release v1.1.0

### Added
- New feature X
- New sensor Y

### Fixed
- Bug fix Z
"

# Push the tag
git push origin v1.1.0
```

### 6. Create GitHub Release

Go to: https://github.com/JoaoPedroBelo/bmw-wallbox-ha/releases/new

**Fill in:**
- **Choose a tag**: Select `v1.1.0`
- **Release title**: `v1.1.0 - Brief Description`
- **Description**: Copy from CHANGELOG.md and format nicely:

```markdown
## What's New in v1.1.0

### ✨ New Features
- Added feature X for better Y
- New sensor Z for monitoring ABC

### 🐛 Bug Fixes
- Fixed issue with XYZ
- Resolved problem with ABC

### 🔧 Improvements
- Performance improvements
- Better error handling

## Installation

Install via HACS:
1. HACS → Integrations → ⋮ → Custom repositories
2. Add: `https://github.com/JoaoPedroBelo/bmw-wallbox-ha`
3. Category: Integration
4. Find "BMW Wallbox (OCPP)" and install
5. Restart Home Assistant

## Upgrade Notes

⚠️ **Breaking Changes** (if any):
- List any breaking changes here
- Include migration steps

## Full Changelog
**Full Changelog**: https://github.com/JoaoPedroBelo/bmw-wallbox-ha/blob/main/CHANGELOG.md
```

Click **"Publish release"**

### 7. Verify Release

After publishing:

1. **Check GitHub Release**: 
   - https://github.com/JoaoPedroBelo/bmw-wallbox-ha/releases
   - Verify it shows correctly

2. **Check HACS Update** (wait 5-15 minutes):
   - HACS checks for updates periodically
   - Users will see update notification
   - Can force check: HACS → Integrations → BMW Wallbox → Redownload

3. **Test Installation**:
   - Try installing the new version in a test instance
   - Verify everything works

## Hotfix Process

If you need to quickly fix a critical bug:

```bash
# Create hotfix from main
git checkout main
git pull

# Make the fix
# ... edit files ...

# Version bump (e.g., 1.1.0 → 1.1.1)
# Update manifest.json and CHANGELOG.md

# Commit and push
git add .
git commit -m "Hotfix: Fix critical bug X"
git push origin main

# Tag and release immediately
git tag -a v1.1.1 -m "Hotfix v1.1.1: Fix critical bug X"
git push origin v1.1.1

# Create GitHub release as above
```

## Pre-release / Beta Versions

For testing before stable release:

```bash
# Use pre-release version numbers
# In manifest.json: "version": "1.1.0-beta.1"

# Create tag
git tag -a v1.1.0-beta.1 -m "Beta release v1.1.0-beta.1"
git push origin v1.1.0-beta.1

# On GitHub Release page:
# ✅ Check "This is a pre-release"
# This won't notify HACS users automatically
```

## Troubleshooting

### Tag Already Exists

If you need to recreate a tag:
```bash
# Delete local tag
git tag -d v1.1.0

# Delete remote tag
git push origin :refs/tags/v1.1.0

# Recreate and push
git tag -a v1.1.0 -m "Release v1.1.0"
git push origin v1.1.0
```

### Release Not Showing in HACS

- Wait 15-30 minutes for HACS to check
- Check if tag format is correct: `v1.1.0` (with 'v' prefix)
- Verify manifest.json version matches tag
- Force HACS refresh: HACS → ⋮ → Reload

### GitHub Actions Failing

- Don't create release until Actions pass
- Check logs: https://github.com/JoaoPedroBelo/bmw-wallbox-ha/actions
- Fix issues and create new version if needed

## Release Checklist

Before creating a release:

- [ ] All changes committed and pushed
- [ ] Tests passing (GitHub Actions green)
- [ ] CHANGELOG.md updated
- [ ] manifest.json version updated
- [ ] Version number follows semantic versioning
- [ ] Documentation updated (if needed)
- [ ] Breaking changes clearly documented
- [ ] Migration guide provided (if breaking changes)
- [ ] Release notes drafted
- [ ] Tag created and pushed
- [ ] GitHub Release created
- [ ] Release announcement posted (optional)
- [ ] Verified HACS update works

## Post-Release

After release:

1. **Monitor Issues**: Watch for bug reports
2. **Check Community Feedback**: Discord, forums, GitHub issues
3. **Plan Next Release**: Start planning next features
4. **Update Projects**: Update project boards if using them

## Automation (Future)

Consider automating releases with:
- GitHub Actions for automatic tagging
- Automated CHANGELOG generation
- Release drafts created automatically
- Notifications to community channels

## Resources

- [Semantic Versioning](https://semver.org/)
- [Keep a Changelog](https://keepachangelog.com/)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github)
- [HACS Documentation](https://hacs.xyz/docs/publish/include)

## Questions?

If you have questions about the release process:
- Check existing releases: https://github.com/JoaoPedroBelo/bmw-wallbox-ha/releases
- Review CHANGELOG: https://github.com/JoaoPedroBelo/bmw-wallbox-ha/blob/main/CHANGELOG.md
- Open discussion: https://github.com/JoaoPedroBelo/bmw-wallbox-ha/discussions



