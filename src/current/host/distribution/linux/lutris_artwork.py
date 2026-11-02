"""Install packaged artwork through Lutris paths, without network requests."""

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path


def install_artwork(here, base, game_id=None):
    from lutris.database import games
    from lutris.util.resources import get_banner_path, get_cover_path, get_icon_path

    slug = "boshy-randomizer"
    if game_id is not None:
        game = games.get_game_by_field(game_id, "id")
        if not game or game.get("installer_slug") != "boshy-randomizer-native":
            raise ValueError("Artwork requires the registered Randomizer entry")
        slug = game["slug"]
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", slug):
        raise ValueError("Invalid Lutris game slug")
    artwork = Path(here) / "artwork"
    targets = {
        "banner.jpg": Path(get_banner_path(slug)),
        "cover.jpg": Path(get_cover_path(slug)),
        "icon.png": Path(get_icon_path(slug)),
    }
    signatures = {
        name: hashlib.sha256((artwork / name).read_bytes()).hexdigest()
        for name in targets
    }
    marker = Path(base) / "lutris-artwork.json"
    try:
        previous = json.loads(marker.read_text())
    except (FileNotFoundError, ValueError):
        previous = {}
    # Applying once leaves later user-selected artwork intact. A missing cache
    # file is restored even if the package version has not changed.
    for name, target in targets.items():
        if previous.get("files", {}).get(name) == signatures[name] and target.is_file():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".boshy-artwork-", dir=target.parent)
        os.close(fd)
        try:
            shutil.copyfile(artwork / name, temporary)
            os.chmod(temporary, 0o644)
            os.replace(temporary, target)
        finally:
            Path(temporary).unlink(missing_ok=True)
    if game_id is not None and previous.get("game_id") != game_id:
        games.update_existing(
            id=game_id,
            has_custom_banner=1,
            has_custom_icon=1,
            has_custom_coverart_big=1,
        )
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"files": signatures, "game_id": game_id}, indent=2))
