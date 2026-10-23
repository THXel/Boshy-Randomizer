#!/usr/bin/env bash
set -eu
cd -- "$(dirname -- "$(readlink -f -- "$0")")"
exec 9>".linux-instance.lock"
flock -n 9 || { zenity --info --text="$(python3 ui_i18n.py 'Der Boshy Randomizer läuft bereits.')"; exit 0; }
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
if python3 native_menu_host.py >>linux-runtime.log 2>&1; then
    exit 0
else
    zenity --error --title='Boshy Randomizer' --text="$(python3 ui_i18n.py 'Der Randomizer konnte nicht weiterlaufen. Bitte schließe gegebenenfalls ein anderes Boshy-Fenster.')\nDetails: $(pwd)/linux-runtime.log"
    exit 1
fi
