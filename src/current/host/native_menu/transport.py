"""Small save-compatible INI mailbox; no window toolkit or process injection."""

import configparser, io, json
from menu_host.store import RC4, atomic


def read(path):
    data = path.read_bytes()
    if not 0 < len(data) < 8192:
        raise ValueError("Native menu mailbox size")
    c = configparser.ConfigParser(interpolation=None)
    c.read_string(RC4(b"BLOB", data).decode("latin1"))
    return {k: int(v) for k, v in c["Menu"].items()}


def write(path, values):
    c = configparser.ConfigParser(interpolation=None)
    c.optionxform = str
    c["Menu"] = {k: str(v) for k, v in values.items()}
    s = io.StringIO()
    c.write(s, space_around_delimiters=False)
    atomic(path, RC4(b"BLOB", s.getvalue().replace("\n", "\r\n").encode("latin1")))


class Mailbox:
    def __init__(self, folder, renderer, model, *, session_begin=None):
        self.folder = folder
        self.session_begin = session_begin
        self.renderer = renderer
        self.model = model
        self.sequence = 0
        self.generation = 0
        self.step = 0
        write(folder / "native-input.ini", {"Sequence": 0, "Key": 0, "X": 0, "Y": 0})
        self.publish()

    def publish(self, step=None, *, state=True):
        if step is not None:
            self.step = step
        from native_menu.options_locale import prepare

        prepare(self.folder, self.model.language)
        self.renderer.render(self.model, self.step)
        self.generation += 1
        write(
            self.folder / "native-view.ini",
            dict(
                Schema=3,
                ArtGeneration=int(self.renderer.art_generation),
                CentreVisible=int(self.model.page == "home" and not self.model.busy),
                CentreX=418 if self.model.busy else 294,
                CentreY=350 if self.model.busy else 365,
                Enabled=1,
                Generation=self.generation,
                Ack=self.sequence,
                Busy=int(self.model.busy),
                Modal=int(self.model.page != "home" or self.model.busy),
                SelectedSlot=int(self.model.slot),
                **(
                    dict(SessionSchema=1, Begin=self.session_begin)
                    if self.session_begin is not None
                    else {}
                ),
            ),
        )
        if not state:
            return
        atomic(
            self.folder / "native-state.json",
            (
                json.dumps(
                    dict(
                        page=self.model.page,
                        focus=self.model.focus,
                        seed=self.model.draft.seed,
                        options=self.model.draft.options,
                        language=self.model.language,
                        slot=self.model.slot,
                        sequence=self.sequence,
                        generation=self.generation,
                        busy=self.model.busy,
                    ),
                    indent=2,
                )
                + "\n"
            ).encode(),
        )

    def discard_entry(self):
        """Acknowledge the Return used by the original Game menu, without selecting a slot."""
        values = read(self.folder / "native-input.ini")
        seq = values.get("sequence")
        if seq == self.sequence + 1 and values.get("key") == 13:
            self.sequence = seq
            self.publish()

    def poll(self):
        try:
            values = read(self.folder / "native-input.ini")
        except (OSError, ValueError, configparser.Error, KeyError):
            return False
        seq = values.get("sequence")
        if seq == self.sequence:
            return False
        if seq != self.sequence + 1:
            raise ValueError("Native menu input sequence")
        key = values.get("key")
        if key not in (
            8,
            9,
            13,
            32,
            107,
            109,
            187,
            189,
            27,
            33,
            34,
            37,
            38,
            39,
            40,
            46,
            116,
            117,
            118,
            1000,
            1001,
        ):
            raise ValueError("Native menu input code")
        self.model.key(key, values.get("x", 0), values.get("y", 0))
        self.sequence = seq
        self.publish()
        return True
