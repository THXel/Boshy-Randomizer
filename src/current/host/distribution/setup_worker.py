"""Setup worker; never starts source games or changes their files."""

import argparse
import json
import sys
import traceback
from pathlib import Path
from distribution import transaction
from distribution.progress import Reporter, Cancelled
from distribution.package_files import specification, checked_files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=("prepare", "activate", "rollback", "uninstall")
    )
    parser.add_argument(
        "--language",
        choices=("english", "german", "spanish", "russian", "japanese"),
        default="english",
    )
    parser.add_argument("--delete-user-data", action="store_true")
    parser.add_argument("--cancel-file", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--payload", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.delete_user_data and args.action != "uninstall":
        parser.error("--delete-user-data is only valid for uninstall")
    config = None
    # Never interrupt activation or uninstall once their commit has begun.
    progress = Reporter(
        cancel_file=args.cancel_file if args.action == "prepare" else None
    )
    try:
        progress("waiting")
        with transaction.installation_lock(args.root):
            if args.action == "prepare":
                if args.source is None or args.payload is None:
                    raise ValueError("Select an original Boshy ZIP or folder")
                spec = specification(args.payload)
                list(checked_files(args.payload, progress))
                version = transaction.valid_version(spec["version"])
                target = args.root / "versions" / version
                if target.exists():
                    transaction.verified_version(args.root, version, progress)
                else:
                    # Configure before loading any game-resource module.
                    from distribution.windows_entry import configure

                    config = configure(args.payload)
                    from distribution.game_patch import apply

                    transaction.install(
                        args.source,
                        args.root,
                        version,
                        spec["game_sha256"],
                        lambda original, output: apply(
                            original,
                            args.payload / "game.bpatch",
                            output,
                            expected_patch=spec["patch_sha256"],
                            expected_target=spec["game_sha256"],
                            progress=progress,
                        ),
                        payload=args.payload,
                        activate_now=False,
                        progress=progress,
                    )
                result = {"prepared": version}
            elif args.action == "activate":
                result = transaction.activate(
                    args.root, specification(args.payload)["version"], progress
                )
            elif args.action == "rollback":
                result = {"restored": str(transaction.rollback(args.root))}
            else:
                from distribution.user_data import checked_user_data, remove_user_data

                if args.delete_user_data:
                    user_data = checked_user_data()
                    if args.report.resolve().is_relative_to(user_data.resolve()):
                        raise ValueError("Removal report must be outside user data")
                result = {"preserved": transaction.uninstall(args.root, progress)}
                if args.delete_user_data:
                    result["removed_user_data"] = remove_user_data()
        progress("ready", 1, 1)
        report = {"passed": True, "action": args.action, "result": result}
        code = 0
        message = ""
    except Exception as error:
        from distribution.import_errors import explanation

        message = explanation(error, args.language)
        report = {
            "passed": False,
            "action": args.action,
            "error": str(error),
            "message": message,
            "error_code": getattr(error, "code", type(error).__name__),
            "details": traceback.format_exc(),
        }
        code = 2 if isinstance(error, Cancelled) else 1
    finally:
        if config is not None:
            config.unlink(missing_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    Path(str(args.report) + ".ini").write_text(
        "[Failure]\nMessage=" + message.replace("\n", " ") + "\n", encoding="utf-16"
    )
    return code


if __name__ == "__main__":
    sys.exit(main())
