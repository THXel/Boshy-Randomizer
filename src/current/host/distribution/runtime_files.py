"""Required bundled Windows runtime files for game support and diagnostics."""

from pathlib import Path

REQUIRED = (
    "python.exe",
    "pythonw.exe",
    "python313.dll",
    "python313.zip",
    "python313._pth",
    "_ctypes.pyd",
    "Lib/site-packages/PIL/__init__.py",
    "Lib/tkinter/__init__.py",
    "Lib/tkinter/ttk.py",
    "Lib/tkinter/filedialog.py",
    "DLLs/_tkinter.pyd",
    "DLLs/tcl86t.dll",
    "DLLs/tk86t.dll",
    "tcl/tcl8.6/init.tcl",
    "tcl/tk8.6/tk.tcl",
)


def validate_runtime(root):
    """Reject incomplete runtime input before creating a staged package.

    File presence complements the real Windows/Wine import and dialog checks;
    it does not prove DLL ABI compatibility or a working display by itself.
    """
    root = Path(root)
    missing = [
        name
        for name in REQUIRED
        if not (root / name).is_file() or (root / name).stat().st_size == 0
    ]
    if missing:
        raise ValueError("Incomplete Windows runtime: " + ", ".join(missing))
