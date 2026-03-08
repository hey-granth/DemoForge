#!/bin/bash
# Build and publish the DemoForge all-in-one Docker image.
#
# Usage:
#   ./scripts/docker-publish.sh                  # build and push :latest
#   ./scripts/docker-publish.sh 0.1.0            # build and push :0.1.0 + :latest
#   ./scripts/docker-publish.sh 0.1.0 --no-push  # build only, no push

set -euo pipefail

REPO="heygranth/demoforge"
VERSION="${1:-}"
NO_PUSH="${2:-}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "Building DemoForge all-in-one image…"

TAGS=("-t" "$REPO:latest")
if [ -n "$VERSION" ] && [ "$VERSION" != "--no-push" ]; then
    TAGS+=("-t" "$REPO:$VERSION")
fi

docker build \
    -f docker/Dockerfile.allinone \
    "${TAGS[@]}" \
    .

echo ""
echo "Build complete."

if [ "$NO_PUSH" = "--no-push" ] || [ "$VERSION" = "--no-push" ]; then
    echo "Skipping push (--no-push)."
    exit 0
fi

echo "Pushing $REPO:latest …"
docker push "$REPO:latest"

if [ -n "$VERSION" ]; then
    echo "Pushing $REPO:$VERSION …"
    docker push "$REPO:$VERSION"
fi

echo ""
echo "Done. Published:"
echo "  $REPO:latest"
[ -n "$VERSION" ] && echo "  $REPO:$VERSION"

