import os

base_folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ini_folder = os.path.join(base_folder, "INI")
room_folder = os.path.join(ini_folder, "Room")
boss_folder = os.path.join(ini_folder, "Boss")

ez_folder = os.path.join(ini_folder, "EzMode")
ez_room = os.path.join(ez_folder, "Room")
ez_boss = os.path.join(ez_folder, "Boss")

rage_folder = os.path.join(ini_folder, "RageMode")
rage_room = os.path.join(rage_folder, "Room")
rage_boss = os.path.join(rage_folder, "Boss")

iwbtb_folder = os.path.join(base_folder, "IWBTB")

save_enc = os.path.join(iwbtb_folder, "SaveFile1.ini")
game_exe = os.path.join(iwbtb_folder, "I Wanna Be The Boshy.exe")

trigger_json = os.path.join(ini_folder, "triggers.json")
pixel_json = os.path.join(ini_folder, "pixel_regions.json")
json_path = os.path.join(ini_folder, "stats.json")
positions_json = os.path.join(ini_folder, "positions.json")

debug_log = os.path.join(ini_folder, "randomizer_debug.log")

custom_folder = os.path.join(base_folder, "Custom")
custom_logo_path = os.path.join(custom_folder, "boshy_randomizer.png")
custom_icon_path = os.path.join(custom_folder, "boshy.png")

window_title = "I Wanna Be The Boshy"
window_title_variants = [
    "I Wanna Be The Boshy",
    "I Wanna Be The Boshy v1.1",
    "I Wanna Be The Boshy (Compatibility Mode)",
    "I Wanna Be The Boshy.exe",
]

poll_interval = 0.05
rc4_key = b"BLOB"

game_absent_grace_s = 30.0
allow_repeats = False
pixel_stability_frames = 2
trigger_pause_s = 2.0
achievement_trigger_delay_s = 1.0
overlays_enabled = True

solgryn_achievement_key = "solgryn"
save_encoding = "latin-1"
