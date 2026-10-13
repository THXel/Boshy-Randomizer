"""Compatibility entry point. All runs use the native menu and engine."""
if __name__ == '__main__':
    import os
    from pathlib import Path
    launcher=Path(__file__).resolve().parents[1]/'start-linux.sh'
    os.execv(str(launcher),[str(launcher)])
