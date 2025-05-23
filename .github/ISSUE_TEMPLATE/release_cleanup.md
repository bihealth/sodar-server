---
name: Release Cleanup
about: Minor tasks and checklist for maintainer to cleanup and prepare a release
title: 'Cleanup and prepare RELEASE_VERSION'
labels: documentation, internal
assignees: 'mikkonie'

---

## Minor Tasks

TBA

## Issues to Add in CHANGELOG

TBA

## Release Checklist

- [ ] Review code style and cleanup
- [ ] Review and update docs entries
- [ ] Ensure REST API versions are up to date and documented
- [ ] Ensure SODAR Core API versioning is correct in API docs
- [ ] Ensure release notes items are linked to documentation where applicable
- [ ] Run `npm audit fix` for Vue app
- [ ] Run `npx update-browserslist-db@latest` for Vue app
- [ ] Update Vue app version with `npm version`
- [ ] Update version in CHANGELOG and SODAR Release Notes doc
- [ ] Update version in docs conf.py
- [ ] Ensure docs can be built without errors
- [ ] Ensure `make spectacular > /dev/null` runs without errors or warnings (until in CI)

## Notes

N/A
