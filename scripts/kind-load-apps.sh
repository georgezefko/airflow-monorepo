#!/usr/bin/env bash
# Load every app image of this checkout into kind. kind doesn't pull from Artifact Registry
# (its tokens expire after an hour), the same as the Airflow image.
# For a team on an older tag, run it from a checkout of that tag: the tags differ by content.
# Usage: scripts/kind-load-apps.sh [kind cluster name]   (needs: gcloud auth configure-docker us-central1-docker.pkg.dev)
set -euo pipefail
cluster=${1:-kind}
python3 "$(dirname "$0")/../teams/platform/lib/app_image.py" | while read -r _dir image; do
  docker pull -q "$image"
  kind load docker-image "$image" --name "$cluster"
done
