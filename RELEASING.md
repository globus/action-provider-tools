# Releasing

- Determine a new version number, `VERSION=...`

- Make sure your repo is on `main` and up to date;
    `git checkout main; git pull`

- Checkout a release branch, `git checkout -b release/$VERSION`

- Update the version number with `poetry version $VERSION`

- Update the changelog, `scriv collect --edit`

- Add, commit, and push the release branch

```
git add pyproject.toml CHANGELOG.rst changelog.d/
git commit -m "Bump version for release v$VERSION"
git push -u origin release/$VERSION
```
_Note: this assumes `origin` is your desired upstream._

- Create a PR against the `production` branch;
    `gh pr create -B production -t "Release v$VERSION"`

- After any changes and approval, merge the PR, checkout `production`, and pull;
    `git checkout production; git pull`

- Create a release tag and push;
    `git tag -s "v$(poetry version -s)" -m "v$(poetry version -s)"`
    `git push --tags`

- Create a GitHub release, which will auto-publish to pypi
    `gh release create "v$(poetry version -s)" --title "v$(poetry version -s)"`

- Merge `production` back to `main`; `git checkout main; git merge production`

- Delete the release branch; `git branch -d release/$VERSION`
