import os

# ======================================================
# CONFIGURATION FILE (Global Paths + Settings)
# ======================================================

# --- Base paths ---
base_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- INI structure ---
ini_folder  = os.path.join(base_folder, "INI")
room_folder = os.path.join(ini_folder, "Room")   # optional (legacy); route/positions kommen aus positions.json
boss_folder = os.path.join(ini_folder, "Boss")   # optional (legacy)

# --- Ez/Rage Mode paths (optional) ---
ez_folder = os.path.join(ini_folder, "EzMode")
ez_room   = os.path.join(ez_folder, "Room")
ez_boss   = os.path.join(ez_folder, "Boss")

rage_folder = os.path.join(ini_folder, "RageMode")
rage_room   = os.path.join(rage_folder, "Room")
rage_boss   = os.path.join(rage_folder, "Boss")

# --- Game folder ---
iwbtb_folder = os.path.join(base_folder, "IWBTB")

# --- Important files ---
save_enc     = os.path.join(iwbtb_folder, "SaveFile1.ini")
game_exe     = os.path.join(iwbtb_folder, "I Wanna Be The Boshy.exe")  # ✅ Originalspielname

# --- JSON configs ---
trigger_json   = os.path.join(ini_folder, "triggers.json")
pixel_json     = os.path.join(ini_folder, "pixel_regions.json")
json_path      = os.path.join(ini_folder, "stats.json")     # für end_stats.py
positions_json = os.path.join(ini_folder, "positions.json") # Rooms & Bosses aus JSON

# --- Logging ---
debug_log = os.path.join(ini_folder, "randomizer_debug.log")

# --- Custom assets ---
custom_folder    = os.path.join(base_folder, "Custom")
custom_logo_path = os.path.join(custom_folder, "boshy_randomizer.png")
custom_icon_path = os.path.join(custom_folder, "boshy.png")

# ======================================================
# GAME / RANDOMIZER SETTINGS
# ======================================================

window_title = "I Wanna Be The Boshy"  # Haupttitel des Fensters
# 👉 Varianten-Namen, wie sie auf manchen Systemen/Versionen erscheinen können:
window_title_variants = [
    "I Wanna Be The Boshy",
    "I Wanna Be The Boshy v1.1",
    "I Wanna Be The Boshy (Compatibility Mode)",
    "I Wanna Be The Boshy.exe",
]

poll_interval = 0.15
rc4_key = b"BLOB"
game_absent_grace_s = 30.0  # ⏳ Grace period, falls Fenster verschwindet

# Optional: wird nur für die Log-Zeile genutzt (safe default)
allow_repeats = False

# ======================================================
# TRIGGER & DETECTION SETTINGS
# ======================================================

pixel_stability_frames = 2
trigger_pause_s = 2.0
achievement_trigger_delay_s = 1.0

# ======================================================
# UI/Overlays
# ======================================================
# Globaler Schalter: wenn False, sind begin_loading_overlay()/end_loading_overlay() No-Op.
overlays_enabled = True

# ======================================================
# MISC
# ======================================================

solgryn_achievement_key = "solgryn"
save_encoding = "latin-1"
