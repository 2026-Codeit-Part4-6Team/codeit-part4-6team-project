"""Remove deployment images older than the current and rollback tags."""

from __future__ import annotations

import os
import re
import subprocess
import sys

SHA_TAG_PATTERN = re.compile(r"[0-9a-f]{40}")


def select_images_to_remove(
    *,
    image_base: str,
    current_tag: str,
    backend_tags: list[str],
    frontend_tags: list[str],
) -> tuple[list[str], str | None]:
    frontend_tag_set = set(frontend_tags)
    rollback_tag = next(
        (
            tag
            for tag in backend_tags
            if tag != current_tag and tag in frontend_tag_set
        ),
        None,
    )
    keep_tags = {current_tag}
    if rollback_tag:
        keep_tags.add(rollback_tag)

    removals = [
        f"{image_base}/{service}:{tag}"
        for service, tags in (
            ("backend", backend_tags),
            ("frontend", frontend_tags),
        )
        for tag in tags
        if tag not in keep_tags
    ]
    return removals, rollback_tag


def list_sha_tags(repository: str) -> list[str]:
    result = subprocess.run(
        ["docker", "image", "ls", "--format", "{{.Tag}}", repository],
        check=True,
        capture_output=True,
        text=True,
    )
    return list(
        dict.fromkeys(
            tag
            for tag in result.stdout.splitlines()
            if SHA_TAG_PATTERN.fullmatch(tag)
        )
    )


def main() -> int:
    image_base = os.environ.get("IMAGE_BASE", "")
    current_tag = os.environ.get("IMAGE_TAG", "")
    if not re.fullmatch(r"[a-z0-9.-]+/[a-z0-9._/-]+", image_base):
        print("IMAGE_BASE has an invalid value", file=sys.stderr)
        return 1
    if not SHA_TAG_PATTERN.fullmatch(current_tag):
        print("IMAGE_TAG must be a full Git commit SHA", file=sys.stderr)
        return 1

    backend_tags = list_sha_tags(f"{image_base}/backend")
    frontend_tags = list_sha_tags(f"{image_base}/frontend")
    if current_tag not in backend_tags or current_tag not in frontend_tags:
        print("current deployment images are missing; refusing cleanup", file=sys.stderr)
        return 1

    removals, rollback_tag = select_images_to_remove(
        image_base=image_base,
        current_tag=current_tag,
        backend_tags=backend_tags,
        frontend_tags=frontend_tags,
    )
    for image in removals:
        subprocess.run(["docker", "image", "rm", image], check=True)

    print(f"Current image retained: {current_tag}")
    if rollback_tag:
        print(f"Rollback image retained: {rollback_tag}")
    else:
        print("No shared rollback image is available yet.")
    print(f"Old deployment images removed: {len(removals)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
