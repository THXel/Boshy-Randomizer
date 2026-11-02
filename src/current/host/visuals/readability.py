"""Retain the original visible silhouette of randomized collidable scenery."""

from PIL import Image, ImageChops, ImageFilter, ImageOps


def preserve_edges(original, randomized):
    """Keep one original edge pixel; texture variation remains inside the shape.

    Padding makes the outside of an opaque tile count as an edge too. Alpha,
    image size and collision geometry are never modified.
    """
    if (
        original.size != randomized.size
        or original.mode != "RGBA"
        or randomized.mode != "RGBA"
    ):
        raise ValueError("Scenery geometry changed")
    alpha = original.getchannel("A")
    if alpha.tobytes() != randomized.getchannel("A").tobytes():
        raise ValueError("Scenery transparency changed")
    visible = alpha.point(lambda a: 255 if a else 0)
    padded = ImageOps.expand(visible, border=1, fill=0)
    inside = padded.filter(ImageFilter.MinFilter(3)).crop(
        (1, 1, original.width + 1, original.height + 1)
    )
    edge = ImageChops.subtract(visible, inside)
    result = Image.composite(original, randomized, edge)
    result.putalpha(alpha)
    return result
