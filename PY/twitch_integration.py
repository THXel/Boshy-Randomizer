# PY/twitch_integration.py
# ======================================================
# Twitch Integration for Boshy Randomizer
#  - Reads twitch_config.json
#  - Starts a TwitchIO bot in a background thread
#  - Listens to chat commands and (optionally) channel point redemptions
#  - Pushes internal commands into a queue read by rando_script
# ======================================================

from __future__ import annotations
import os
import json
import threading
import queue
from typing import Optional, Dict, Any

try:
    from PY.logger import log
except ModuleNotFoundError:
    # Fallback, falls direkt ausgeführt
    def log(msg: str):
        print(msg)


# Globale Queue, die der Randomizer abfragt
_command_queue: "queue.Queue[str]" = queue.Queue()
_config: Optional[Dict[str, Any]] = None
_bot_thread: Optional[threading.Thread] = None


# ------------------------------------------------------
# Öffentliche API
# ------------------------------------------------------
def get_command_queue() -> "queue.Queue[str]":
    """Queue, aus der rando_script die Twitch-Kommandos lesen kann."""
    return _command_queue


def start_twitch_listener(config_path: str, stop_event: threading.Event) -> None:
    """
    Lädt die Konfiguration und startet (falls enabled) den Twitch-Bot
    in einem separaten Thread.
    """
    global _config, _bot_thread

    _config = _load_twitch_config(config_path)
    if not _config:
        log("🟣 Twitch: Keine gültige Konfiguration gefunden (twitch_config.json).")
        return

    if not _config.get("enabled", False):
        log("🟣 Twitch: Integration ist deaktiviert (enabled = false).")
        return

    # Sicherstellen, dass zwingende Felder gesetzt sind
    required = ["channel_name", "oauth_token"]
    missing = [k for k in required if not _config.get(k)]
    if missing:
        log(f"🟣 Twitch: Fehlende Felder in Config: {', '.join(missing)}")
        return

    if _bot_thread and _bot_thread.is_alive():
        log("🟣 Twitch: Listener läuft bereits.")
        return

    _bot_thread = threading.Thread(
        target=_run_bot_thread,
        args=(stop_event,),
        daemon=True,
        name="BoshyTwitchBot",
    )
    _bot_thread.start()
    log("🟣 Twitch: Listener-Thread gestartet.")


# ------------------------------------------------------
# interne Helfer
# ------------------------------------------------------
def _load_twitch_config(path: str) -> Optional[Dict[str, Any]]:
    try:
        if not os.path.isfile(path):
            log(f"🟣 Twitch: Config-Datei nicht gefunden: {path}")
            return None
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg
    except Exception as e:
        log(f"🟣 Twitch: Fehler beim Laden der Config: {e}")
        return None


def _run_bot_thread(stop_event: threading.Event) -> None:
    """
    Startet den TwitchIO-Bot. Läuft in einem Hintergrund-Thread.
    stop_event wird vom Hauptprogramm gesetzt, wenn es beendet wird.
    """
    from twitchio.ext import commands

    channel = _config["channel_name"]
    token = _config["oauth_token"]
    reward_map: Dict[str, str] = _config.get("reward_map", {})

    # Du kannst hier optional ein Prefix anpassen, z.B. "!" o.ä.
    bot = commands.Bot(
        token=token,
        prefix="!",
        initial_channels=[channel],
        heartbeat=30.0,
    )

    log(f"🟣 Twitch: Bot verbindet sich zu #{channel} ...")

    # ------------------------
    # Chat-Befehle -> Commands
    # ------------------------

    @bot.event()
    async def event_ready():
        log(f"🟣 Twitch: Eingeloggt als {bot.nick}")

        # HINWEIS:
        # Channel Points können über PubSub/EventSub gehört werden.
        # TwitchIO unterstützt PubSub – hier nur Platzhalter:
        #   from twitchio.ext import pubsub
        #   bot.pubsub = pubsub.PubSubPool(bot)
        #   user_id = ...  # Twitch-User-ID
        #   await bot.pubsub.subscribe_channel_points(user_id, token)
        #
        # und dann ein event:
        #   @bot.event()
        #   async def event_pubsub_channel_points(event):
        #       title = event.reward.title
        #       internal = reward_map.get(title)
        #       if internal:
        #           _push_command(internal)

    @bot.event()
    async def event_message(message):
        # Eigenen Bot ignorieren
        if message.echo:
            return

        text = message.content.strip().lower()

        # Beispiel: Chat-Befehle alternativ/zusätzlich zu Channel Points:
        # (Du kannst die Mappings auch in die Config legen)

        if text.startswith("!randomchar"):
            _push_command("random_character")
        elif text.startswith("!nextlevel"):
            _push_command("next_level")
        elif text.startswith("!randitem+"):
            _push_command("add_item")
        elif text.startswith("!randitem-"):
            _push_command("remove_item")
        elif text.startswith("!suicide") or text.startswith("!q"):
            _push_command("press_q")
        elif text.startswith("!reset") or text.startswith("!r"):
            _push_command("press_r")

        await bot.handle_commands(message)

    # ------------------------
    # Optional: echte Commands
    # ------------------------

    @bot.command(name="randomchar")
    async def cmd_randomchar(ctx):
        _push_command("random_character")
        await ctx.send("🔁 Random Character ausgelöst!")

    @bot.command(name="next")
    async def cmd_next(ctx):
        _push_command("next_level")
        await ctx.send("⏭ Nächstes Level!")

    @bot.command(name="suicide")
    async def cmd_suicide(ctx):
        _push_command("press_q")

    @bot.command(name="reset")
    async def cmd_reset(ctx):
        _push_command("press_r")

    # ------------------------
    # Stop-Handling
    # ------------------------
    #
    # twitchio.run() blockiert – da wir in einem Thread sind, ist das ok.
    # Wir haben hier kein eingebautes stop_event, aber wenn dein Hauptprozess
    # beendet wird, geht der Thread sowieso mit down.

    try:
        bot.run()
    except Exception as e:
        log(f"🟣 Twitch: Bot-Fehler: {e}")


def _push_command(cmd: str) -> None:
    """Legt ein internes Kommando in die Queue, die der Randomizer abarbeitet."""
    try:
        _command_queue.put_nowait(cmd)
        log(f"🟣 Twitch: Command in Queue: {cmd}")
    except Exception as e:
        log(f"🟣 Twitch: Fehler beim Queue-Push ({cmd}): {e}")
