# Releasing

- Determine a new version number, `VERSION=...`
- Checkout `main` and ensure you are up to date, `git checkout main; git pull`
- Create and checkout a release branch, `git checkout -b release/$VERSION`
- Update the version number with `poetry version $VERSION`
- Update the changelog, `scriv collect --edit`
- Add, commit, and push
    `git commit -m "Bump version for release v$VERSION"`
- Fast-forward merge the release branch to the `production` branch
    `git checkout production && git merge --no-ff release/$VERSION`
- Create a release tag and push,
    `git tag -s "v$(poetry version -s)" -m "v$(poetry version -s)"`
- Create a GitHub release, which will auto-publish to pypi
    `gh release create "v$(poetry version -s)" --title "v$(poetry version -s)"`
- Merge `production` back to `main`, `git checkout main; git merge production`
- Delete the release branch, `git branch -d release/$VERSION`
