"""Native application display flags: scalable client area with an explicitly chosen aspect.

Constants follow reference-clickteam-sdk/Inc/Cncy.h. Gameplay remains 640x480;
Fusion scales presentation and mouse coordinates without changing world geometry.
"""


def install(writer):
    original = writer.map_app_words

    def flags(old, new, other, extended, notes):
        # GA_STRETCH; clear GANF_NOMAXIMIZEBOX/GANF_NOTHICKFRAME;
        # Clear AH2OPT_KEEPSCREENRATIO so 16:9 can stretch the 4:3 canvas.
        # The host/native size rows enforce the user-selected outer ratio.
        return original(
            old | 0x0010, new & ~0x0060, other, (extended or 0) & ~0x0001, notes
        )

    writer.map_app_words = flags


def install_intro_lifetime(app_type):
    """A private application-lifetime flag; the engine resets it on F2."""
    original = app_type.globals

    def globals_with_intro(self):
        values, strings = original(self)
        assert values["count"] == 24
        values = dict(
            values, count=25, values=[*values["values"], 0], types=[*values["types"], 0]
        )
        return values, strings

    app_type.globals = globals_with_intro
