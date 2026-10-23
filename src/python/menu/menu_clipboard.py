"""Keep the X11 clipboard owner alive while the native menu is open."""


class Clipboard:
    def __init__(self):
        import tkinter as tk

        self.root = tk.Tk()
        self.root.withdraw()

    def get(self):
        value = self.root.clipboard_get()
        if len(value) > 4096:
            raise ValueError('Der eingefügte Seed ist zu lang.')
        return value

    def put(self, value):
        self.root.clipboard_clear()
        self.root.clipboard_append(value)
        self.root.update()

    def pump(self):
        self.root.update()

    def close(self):
        self.root.destroy()
