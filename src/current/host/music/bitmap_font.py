"""Render the imported local Undertale bitmap font without smoothing."""
import json
from PIL import Image


class BitmapFont:
    def __init__(self, root, name="fnt_main"):
        from music.import_undertale import local_file
        data = json.loads(local_file(root, name + ".json").read_text())
        if data["name"] != name or data["line_height"] != 36:
            raise ValueError("Undertale font identity")
        with Image.open(local_file(root, name + ".png")) as image:
            if image.format != "PNG" or max(image.size) > 4096:
                raise ValueError("Undertale font atlas")
            self.atlas = image.convert("RGBA")
        self.glyphs = {}
        for row in data["glyphs"]:
            code, x, y, width, height, shift, offset = (row[k] for k in
                ("code", "x", "y", "width", "height", "shift", "offset"))
            if any(type(v) is not int for v in (code,x,y,width,height,shift,offset)):
                raise ValueError("Undertale font metrics")
            if not (0 <= x <= x+width <= self.atlas.width and
                    0 <= y <= y+height <= self.atlas.height and 0 <= shift <= 64 and abs(offset) <= 64):
                raise ValueError("Undertale glyph bounds")
            self.glyphs[chr(code)] = (self.atlas.crop((x,y,x+width,y+height)), shift, offset)
        if not set("Boshy!Stay determined.R") <= self.glyphs.keys():
            raise ValueError("Incomplete Undertale font")
        self.line_height = data["line_height"]

    def draw(self, image, text, position):
        start, y = position
        x = start
        for char in text:
            if char == "\n":
                x = start
                y += self.line_height
            else:
                glyph, advance, offset = self.glyphs[char]
                image.alpha_composite(glyph, (x + offset, y))
                x += advance


class CyrillicFont:
    """Use the bundled Cyrillic font at a small pixel grid, scaled without blur."""
    def __init__(self):
        from PIL import ImageFont
        from platform_support.fonts import font_path
        self.font = ImageFont.truetype(font_path("ru"), 12)

    def draw(self, image, text, position):
        from PIL import ImageDraw
        mask = Image.new("1", (200, 40))
        ImageDraw.Draw(mask).multiline_text((0, 0), text, font=self.font, fill=1, spacing=6)
        alpha = mask.convert("L").resize((400, 80), Image.Resampling.NEAREST)
        layer = Image.new("RGBA", alpha.size, "white")
        layer.putalpha(alpha)
        image.alpha_composite(layer, position)
