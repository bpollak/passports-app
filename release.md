# Release Process

Every merged change that should be deployed needs a GitHub tag. After the tag is created, the Helm chart must be updated to use that same tag.

This repository currently uses semver-style release tags with a `v` prefix, for example `v0.2.0`. Continue that style for new releases, such as `v0.2.1` for a patch release or `v0.3.0` for a larger feature release.

## Tagging After Merge

Create the tag from the merged `main` commit, not from the feature branch.

### Human

1. Open the repository in GitHub.
2. On the repository home page, find the **Releases** card in the right sidebar.
3. Click **Create a new release**.
4. Click **Choose a tag**, enter the next semver-style tag, such as `v0.2.1`, and target the merged `main` branch.
5. Use the tag as the release title, add brief notes if helpful, and publish the release.
6. Confirm the GitHub Actions image workflow started for the tag.

### AI Agent

1. Confirm the PR has been merged.
2. Sync `main` and tags:

   ```bash
   git fetch origin main --tags
   git switch main
   git pull --ff-only origin main
   ```

3. Confirm the commit to release:

   ```bash
   git log --oneline -1
   ```

4. Pick the next semver-style tag after the latest existing tag:

   ```bash
   git tag --list "v*" --sort=version:refname
   ```

5. Create and push the new tag:

   ```bash
   git tag -a v0.2.1 -m "v0.2.1"
   git push origin v0.2.1
   ```

6. Verify the GitHub Actions image workflow started for the tag.

## Helm Chart Update

After the GitHub tag exists, the deployed Helm chart needs to be updated so `image.tag` matches that release tag.

The Helm chart update is not currently automated from this repository. Send the release tag to the TritonAI team and ask them to update the chart deployment:

tritonai@ucsd.edu
