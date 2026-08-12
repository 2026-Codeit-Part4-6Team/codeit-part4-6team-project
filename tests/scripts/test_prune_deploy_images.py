from scripts.prune_deploy_images import select_images_to_remove


def test_keeps_current_and_newest_shared_rollback_tag() -> None:
    removals, rollback_tag = select_images_to_remove(
        image_base="registry.example/team6",
        current_tag="current",
        backend_tags=["current", "backend-only", "previous", "old"],
        frontend_tags=["current", "previous", "frontend-only", "old"],
    )

    assert rollback_tag == "previous"
    assert removals == [
        "registry.example/team6/backend:backend-only",
        "registry.example/team6/backend:old",
        "registry.example/team6/frontend:frontend-only",
        "registry.example/team6/frontend:old",
    ]


def test_keeps_current_when_no_shared_rollback_tag_exists() -> None:
    removals, rollback_tag = select_images_to_remove(
        image_base="registry.example/team6",
        current_tag="current",
        backend_tags=["current", "backend-only"],
        frontend_tags=["current", "frontend-only"],
    )

    assert rollback_tag is None
    assert removals == [
        "registry.example/team6/backend:backend-only",
        "registry.example/team6/frontend:frontend-only",
    ]
