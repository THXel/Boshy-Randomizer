"""Release gates are positive evidence, never inferred from a unit-test count."""

REQUIRED = (
    "source_and_binary_identity",
    "automated_regressions",
    "all_exit_cases",
    "sprite_readability",
    "long_session",
    "windows_runtime",
    "linux_runtime",
    "original_resource_patch",
    "windows_clean_install",
    "linux_clean_install",
    "update_rollback",
    "uninstall",
)


def validate(manifest, *, platform):
    if platform not in ("windows", "linux"):
        raise ValueError("Unknown package platform")
    if manifest.get("schema") != 1:
        raise ValueError("Unsupported release manifest")
    game_hash = manifest.get("game_sha256")
    if (
        not isinstance(game_hash, str)
        or len(game_hash) != 64
        or any(c not in "0123456789abcdef" for c in game_hash)
    ):
        raise ValueError("Missing game identity")
    evidence = manifest.get("gates", {})
    required = set(REQUIRED) - (
        {"windows_runtime", "windows_clean_install"}
        if platform == "linux"
        else {"linux_runtime", "linux_clean_install"}
    )
    missing = sorted(
        key
        for key in required
        if not (
            evidence.get(key, {}).get("status") == "passed"
            and evidence[key].get("game_sha256") == game_hash
            and evidence[key].get("report")
        )
    )
    if missing:
        raise ValueError("Package is not verified: " + ", ".join(missing))
    return True
