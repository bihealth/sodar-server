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
- [ ] Update `SODAR_API_DEFAULT_VERSION` and `SODAR_API_ALLOWED_VERSIONS`
- [ ] Run `npx update-browserslist-db@latest` for Vue app
- [ ] Update Vue app version with `npm version`
- [ ] Update version in CHANGELOG and SODAR Release Notes doc
- [ ] Update version in docs conf.py
- [ ] Ensure both SODAR and SODAR Core API versioning is correct in API docs
- [ ] Ensure docs can be built without errors

## Notes

N/A
