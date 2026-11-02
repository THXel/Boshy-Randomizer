"""Fit the existing logo to launcher artwork sizes, without cropping/stretching."""

from pathlib import Path


def build_artwork(source, destination):
    import gi
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import GdkPixbuf

    destination = Path(destination)
    destination.mkdir(parents=True)
    logo = GdkPixbuf.Pixbuf.new_from_file(str(source))
    sizes = {"banner.jpg": (368, 138), "cover.jpg": (528, 704), "icon.png": (128, 128)}
    for name, (width, height) in sizes.items():
        canvas = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, width, height)
        canvas.fill(0x14232BFF)
        scale = min(width * .94 / logo.get_width(), height * .94 / logo.get_height())
        w, h = max(1, round(logo.get_width() * scale)), max(1, round(logo.get_height() * scale))
        scaled = logo.scale_simple(w, h, GdkPixbuf.InterpType.BILINEAR)
        x, y = (width-w)//2, (height-h)//2
        scaled.composite(canvas, x, y, w, h, x, y, 1, 1, GdkPixbuf.InterpType.BILINEAR, 255)
        png = name.endswith(".png")
        canvas.savev(str(destination / name), "png" if png else "jpeg",
                     [] if png else ["quality"], [] if png else ["100"])
