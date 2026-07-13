# Release Process

This package is published to PyPI with `uv publish` from GitHub Actions.

## One-time PyPI Setup

Configure PyPI Trusted Publishing for the `liferay-context-builder` project:

- Owner: `mordonez`
- Repository: `liferay-context-builder`
- Workflow: `publish.yml`
- Environment: leave empty unless the workflow is later changed to use a
  GitHub environment

Do not store a long-lived PyPI token in GitHub secrets for the normal release
flow. The publish workflow uses GitHub OIDC (`id-token: write`) and
`uv publish --trusted-publishing always`.

Reference docs:

- PyPI: https://docs.pypi.org/trusted-publishers/using-a-publisher/
- uv: https://docs.astral.sh/uv/guides/package/

## Release

1. Update `version` in `pyproject.toml`.
2. Run local checks:

   ```bash
   uv run ruff check .
   uv run --with pytest python -m pytest
   uv build
   ```

3. Commit with a conventional commit message.
4. Tag the release:

   ```bash
   git tag vX.Y.Z
   git push origin main --tags
   ```

The `Publish` GitHub Actions workflow builds the source distribution and wheel
from the tag and uploads `dist/*` to PyPI.

For a manual publish of the current branch, run the `Publish` workflow from the
GitHub Actions UI. Prefer tag releases for normal PyPI versions so the published
artifact is tied to an immutable Git ref.

## Build Artifacts Without Publishing

The `CI` workflow builds the package on every PR and push to `main`. The Python
3.13 job uploads the generated `dist/*` files as a GitHub Actions artifact named
`distributions`, so package contents can be inspected before publishing.
