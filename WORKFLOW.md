# Development workflows

This document prescribes how to branch and merge code in this project.

When provided, shell commands are designed to minimize human interaction.
In most cases the commands can be copied and pasted.

Some commands may not be available until the virtual environment is created and activated.


## Table of contents

* [Version numbering](#version-numbering)
* [Priority git branches](#priority-git-branches)
* [Everyday development](#everyday-development)
* [Preparing a hotfix release](#preparing-a-hotfix-release)


## Version numbering

This project uses Semantic Versioning.
However, the tools have not reached version `1` yet,
so at this time it's acceptable to change the API when incrementing the minor version.

```text
<major>.<minor>.<patch>
╰┬────╯ ╰┬────╯ ╰┬────╯
 │       │       ╰─ The patch version.
 │       │          Increments when non-breaking changes are made.
 │       │          Resets to 0 when <major> or <minor> changes.
 │       │
 │       ╰─ The minor version.
 │          Increments when breaking changes are made.
 │          Resets to 0 when <major> changes.
 │
 ╰─ The major version.
    Currently this does not increment.
```


## Priority git branches

There are several git branches that have assigned significance.

### `main`

`main` tracks all repository changes. Every branch must eventually merge to `main`.

### `production`

`production` tracks code that is, or is about to be, deployed to PyPI or ReadTheDocs.
Each merge commit must be accompanied by a git tag representing the released version.


## Everyday development

"Everyday" development refers to repository changes that are not intended for out-of-cycle release to the production environment.
This may include non-critical bug fixes, documentation updates, CI/CD changes, dependency updates, or other tooling changes.

Feature development begins by creating a new branch off of `main`.

The script below can create a branch off of `main`:

```shell
read -p "Enter the feature branch name: " BRANCH_NAME

# Everything below can run unmodified.
git checkout main
git pull
git checkout -b "$BRANCH_NAME"
```

Feature branches are merged back to `main`, and only to `main`.


## Preparing a hotfix release

If a bug is found in production and must be fixed immediately, this requires a hotfix release.
In general, dependency updates should not be in-scope for hotfix releases.

Hotfix releases begin by creating a branch off of `production`:

```shell
read -p "Enter the hotfix release version: " NEW_VERSION
# Everything below can run unmodified.
BRANCH_NAME="hotfix/$NEW_VERSION"
git checkout production
git pull origin
git checkout -b "$BRANCH_NAME"
```

After creating the hotfix branch, fix that bug, create a changelog fragment
and commit the changes in the hotfix branch!

Next, proceed to the [Merging release branches](#merging-release-branches) section.
