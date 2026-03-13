#!/bin/bash
set -euo pipefail

VERSION="${1:-}"
TITLE="${2:-}"

if [[ -z "$VERSION" ]]; then
    echo "Usage: ./release.sh <version> [title]"
    echo "Example: ./release.sh 1.2.3"
    echo "Example: ./release.sh 1.2.3 \"Some Catchy Name\""
    exit 1
fi

# Strip leading 'v' if provided — version numbers in files are bare,
# git tag gets the v prefix
VERSION="${VERSION#v}"
TAG="v$VERSION"
TITLE="${TITLE:-$TAG}"

# Auto-detect project name from meson.build
PROJECT_NAME=$(grep -oP "^project\(\s*'\K[^']+" meson.build)
if [[ -z "$PROJECT_NAME" ]]; then
    echo "ERROR: Could not detect project name from meson.build"
    exit 1
fi

echo "==> Releasing $PROJECT_NAME $TAG"

# 1. Update version in meson.build, PKGBUILD, and Python package
sed -i "0,/version: '[^']*'/{s/version: '[^']*'/version: '$VERSION'/}" meson.build
sed -i "s/^pkgver=.*/pkgver=$VERSION/" PKGBUILD
sed -i "s/^VERSION = \".*\"/VERSION = \"$VERSION\"/" "$PROJECT_NAME/__init__.py"

# 2. Generate release notes before tagging
PREV_TAG=$(git tag --sort=-version:refname | head -1)
if [[ -n "$PREV_TAG" ]]; then
    RELEASE_NOTES=$(git log --pretty=format:"- %s" "$PREV_TAG..HEAD" | grep -v -E "^- (Release |first commit)")
else
    RELEASE_NOTES=$(git log --pretty=format:"- %s" | grep -v -E "^- (Release |first commit)")
fi
echo "==> Release notes:"
echo "$RELEASE_NOTES"

# 3. Commit (if there are changes) and tag
git add meson.build PKGBUILD "$PROJECT_NAME/__init__.py"
if ! git diff --cached --quiet; then
    git commit -m "Release $TAG"
else
    echo "==> Version already set to $VERSION, skipping commit"
fi
git tag "$TAG"

# 4. Push commit and tag to all remotes
for remote in $(git remote); do
    echo "==> Pushing to $remote"
    git push "$remote" HEAD "$TAG"
done

# 4. Build Arch package
echo "==> Building Arch package"
makepkg -sf --noconfirm
ARCH_PKG=$(ls -t ./*.pkg.tar.zst 2>/dev/null | grep -v debug | head -1)

# 5. Build .deb package via meson install + nfpm
echo "==> Building .deb package"
PKGDESC=$(grep -oP "^pkgdesc=\"\K[^\"]+" PKGBUILD || echo "$PROJECT_NAME")
PKGLICENSE=$(grep -oP "^license=\('\K[^']+" PKGBUILD || echo "MIT")

# Install into a staging directory to capture all files
DEB_STAGING="$(pwd)/deb-staging"
rm -rf "$DEB_STAGING"
meson setup builddir --prefix=/usr --wipe
meson compile -C builddir
DESTDIR="$DEB_STAGING" meson install -C builddir --no-rebuild

# Generate nfpm contents from the staged install tree
CONTENTS=""
while IFS= read -r file; do
    dst="${file#"$DEB_STAGING"}"
    CONTENTS+="  - src: $file
    dst: $dst
"
done < <(find "$DEB_STAGING" -type f)

cat > /tmp/nfpm-release.yaml <<NFPM
name: $PROJECT_NAME
arch: amd64
version: $VERSION
maintainer: mk
description: $PKGDESC
license: $PKGLICENSE
depends:
  - python3
  - gir1.2-gtk-4.0
  - gir1.2-adw-1
  - gir1.2-webkit-6.0
  - python3-gi
  - python3-markdown
contents:
$CONTENTS
NFPM

VERSION="$VERSION" nfpm package -p deb -f /tmp/nfpm-release.yaml
rm -rf "$DEB_STAGING"
DEB_PKG=$(ls -t "${PROJECT_NAME}"*.deb 2>/dev/null | head -1)

# 6. Create releases
RELEASE_ASSETS=()
[[ -n "${ARCH_PKG:-}" ]] && RELEASE_ASSETS+=("$ARCH_PKG")
[[ -n "${DEB_PKG:-}" ]] && RELEASE_ASSETS+=("$DEB_PKG")

# GitHub release — find the github remote by URL
GITHUB_REMOTE=""
for remote in $(git remote); do
    if git remote get-url "$remote" 2>/dev/null | grep -q github.com; then
        GITHUB_REMOTE="$remote"
        break
    fi
done
if [[ -n "$GITHUB_REMOTE" ]] && command -v gh &>/dev/null; then
    echo "==> Creating GitHub release (remote: $GITHUB_REMOTE)"
    GH_REPO=$(git remote get-url "$GITHUB_REMOTE" | sed 's|.*github.com[:/]||;s|\.git$||')
    gh release create "$TAG" "${RELEASE_ASSETS[@]}" \
        --repo "$GH_REPO" \
        --title "$TITLE" \
        --notes "$RELEASE_NOTES"
    echo "==> GitHub release created"
fi

# Forgejo release via API
REMOTE_URL=$(git remote get-url origin 2>/dev/null || true)
# Parse hostname and repo path from both ssh:// and scp-style URLs
if [[ "$REMOTE_URL" =~ ^ssh://[^@]+@([^/]+)/(.+)$ ]]; then
    FORGEJO_URL="${BASH_REMATCH[1]}"
    REPO_PATH="${BASH_REMATCH[2]%.git}"
elif [[ "$REMOTE_URL" =~ ^[^@]+@([^:]+):(.+)$ ]]; then
    FORGEJO_URL="${BASH_REMATCH[1]}"
    REPO_PATH="${BASH_REMATCH[2]%.git}"
else
    FORGEJO_URL=""
    REPO_PATH=""
fi
if [[ -n "$FORGEJO_URL" && -n "${FORGEJO_TOKEN:-}" ]]; then
    echo "==> Creating Forgejo release on $FORGEJO_URL ($REPO_PATH)"

    # Check if release already exists for this tag
    EXISTING=$(curl -s "https://$FORGEJO_URL/api/v1/repos/$REPO_PATH/releases/tags/$TAG" \
        -H "Authorization: token $FORGEJO_TOKEN")
    EXISTING_ID=$(echo "$EXISTING" | jq -r '.id // empty')

    if [[ -n "$EXISTING_ID" ]]; then
        echo "==> Release for $TAG already exists (id=$EXISTING_ID), deleting..."
        curl -s -X DELETE "https://$FORGEJO_URL/api/v1/repos/$REPO_PATH/releases/$EXISTING_ID" \
            -H "Authorization: token $FORGEJO_TOKEN"
    fi

    COMMIT_SHA=$(git rev-parse HEAD)
    RELEASE_JSON=$(curl -s -X POST "https://$FORGEJO_URL/api/v1/repos/$REPO_PATH/releases" \
        -H "Authorization: token $FORGEJO_TOKEN" \
        -H "Content-Type: application/json" \
        -d "$(jq -n --arg tag "$TAG" --arg title "$TITLE" --arg body "$RELEASE_NOTES" --arg sha "$COMMIT_SHA" \
            '{tag_name: $tag, name: $title, body: $body, target_commitish: $sha}')")

    RELEASE_ID=$(echo "$RELEASE_JSON" | jq -r '.id')

    if [[ "$RELEASE_ID" != "null" && -n "$RELEASE_ID" ]]; then
        for asset in "${RELEASE_ASSETS[@]}"; do
            echo "==> Uploading $asset to Forgejo"
            curl -s -X POST "https://$FORGEJO_URL/api/v1/repos/$REPO_PATH/releases/$RELEASE_ID/assets" \
                -H "Authorization: token $FORGEJO_TOKEN" \
                -F "attachment=@$asset"
        done
        echo "==> Forgejo release created"
    else
        echo "WARNING: Failed to create Forgejo release"
        echo "$RELEASE_JSON"
    fi
fi

echo ""
echo "==> Done! Released $PROJECT_NAME $TAG"
