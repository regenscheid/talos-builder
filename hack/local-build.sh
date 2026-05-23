#!/usr/bin/env bash
# Local build wrapper that mirrors the GitHub Actions workflow.
#
# Runs `make <args>` inside an ubuntu:24.04 linux/arm64 container,
# with the host Docker socket bind-mounted so all `docker buildx`
# invocations issued by the make targets execute on the host's
# BuildKit daemon (no docker-in-docker; same effective execution as
# the CI runner).
#
# Usage:
#   hack/local-build.sh checkouts patches
#   hack/local-build.sh kernel
#   hack/local-build.sh pi5
#
# Override env vars by prefixing the call:
#   PUSH=false hack/local-build.sh kernel
#   REGISTRY=ghcr.io REGISTRY_USERNAME=regenscheid hack/local-build.sh installer

set -euo pipefail

REGISTRY="${REGISTRY:-localhost:5005}"
REGISTRY_USERNAME="${REGISTRY_USERNAME:-regenscheid}"
TALOS_VERSION="${TALOS_VERSION:-v1.13.2}"
PUSH="${PUSH:-true}"

# The local registry runs on the host as a container; from inside another
# container, reach it via host.docker.internal. The host's BuildKit daemon
# (the one our buildx pushes go through) also resolves it that way.
if [[ "$REGISTRY" == "localhost:"* ]]; then
  PORT="${REGISTRY#localhost:}"
  HOST_REGISTRY="host.docker.internal:${PORT}"
else
  HOST_REGISTRY="$REGISTRY"
fi

# Workspace is the talos-builder repo root.
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

docker run --rm \
  --platform linux/arm64 \
  -v "$REPO_ROOT":/workspace \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -w /workspace \
  -e REGISTRY="$HOST_REGISTRY" \
  -e REGISTRY_USERNAME="$REGISTRY_USERNAME" \
  -e TALOS_VERSION="$TALOS_VERSION" \
  -e PUSH="$PUSH" \
  --add-host=host.docker.internal:host-gateway \
  ubuntu:24.04 \
  bash -c '
    set -e
    export DEBIAN_FRONTEND=noninteractive
    if ! command -v make >/dev/null 2>&1; then
      apt-get update -qq
      apt-get install -y -qq --no-install-recommends \
        make git curl ca-certificates xz-utils \
        docker.io
      # crane for the installer push step
      CRANE_VER=v0.20.5
      curl -fsSL -o /tmp/crane.tar.gz \
        "https://github.com/google/go-containerregistry/releases/download/${CRANE_VER}/go-containerregistry_Linux_arm64.tar.gz"
      tar -xzf /tmp/crane.tar.gz -C /usr/local/bin/ crane
      rm /tmp/crane.tar.gz
    fi
    git config --global --add safe.directory /workspace
    git config --global --add safe.directory "/workspace/checkouts/*"
    git config --global user.email "local-build@regenscheid"
    git config --global user.name "local-build"
    make TALOS_VERSION="${TALOS_VERSION}" \
         REGISTRY="${REGISTRY}" \
         REGISTRY_USERNAME="${REGISTRY_USERNAME}" \
         PUSH="${PUSH}" \
         "$@"
  ' -- "$@"
