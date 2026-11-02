"""Windows 8+ IFileOperation recycling with a permanent-delete veto.

Uses the platform SDK interface layout. PreDeleteItem rejects operations without
TSF_DELETE_RECYCLE_IF_POSSIBLE; neither SHFileOperation nor hard deletion is a fallback.
"""

import ctypes as c
import uuid
from ctypes import wintypes as w

P = c.c_void_p
H = c.c_long
CALL = c.WINFUNCTYPE


def guid(value):
    return (c.c_ubyte * 16).from_buffer_copy(uuid.UUID(value).bytes_le)


FILE_OPERATION = guid("3ad05575-8857-4850-9277-11b85bdb8e09")
I_OPERATION = guid("947aab5f-0a5c-4c13-b4d6-4bf7836fc9f8")
I_ITEM = guid("43826d1e-e718-42ee-bc55-a1e261c37bfe")
I_SINK = guid("04b0f1a7-9490-44bc-96e1-4296a31252e2")
I_UNKNOWN = guid("00000000-0000-0000-c000-000000000046")


def checked(result):
    if result < 0:
        raise OSError("Recycle Bin operation failed (0x%08x)" % (result & 0xFFFFFFFF))
    return result


def method(pointer, index, result, *arguments):
    table = c.cast(pointer, c.POINTER(c.POINTER(P))).contents
    return CALL(result, P, *arguments)(table[index])


class Sink:
    def __init__(self):
        self.refs = 1
        self.recycled = False
        self.blocked = False
        self.result = None
        # IUnknown, then IFileOperationProgressSink in SDK order.
        signatures = [
            (P, c.POINTER(P)),
            (),
            (),
            (),
            (H,),
            (w.DWORD, P, P),
            (w.DWORD, P, P, H, P),
            (w.DWORD, P, P, P),
            (w.DWORD, P, P, P, H, P),
            (w.DWORD, P, P, P),
            (w.DWORD, P, P, P, H, P),
            (w.DWORD, P),
            (w.DWORD, P, H, P),
            (w.DWORD, P, P),
            (w.DWORD, P, P, P, w.DWORD, H, P),
            (w.UINT, w.UINT),
            (),
            (),
            (),
        ]
        handlers = {
            0: self.query,
            1: self.add_ref,
            2: self.release,
            11: self.pre_delete,
            12: self.post_delete,
        }
        self.callbacks = [
            CALL(w.ULONG if i in (1, 2) else H, P, *args)(
                handlers.get(i, lambda *unused: 0)
            )
            for i, args in enumerate(signatures)
        ]
        self.table = (P * len(self.callbacks))(
            *(c.cast(fn, P) for fn in self.callbacks)
        )
        self.instance = P(c.addressof(self.table))
        self.pointer = c.cast(c.pointer(self.instance), P)

    def query(self, this, iid, target):
        if c.string_at(iid, 16) not in (bytes(I_UNKNOWN), bytes(I_SINK)):
            target[0] = None
            return -2147467262  # E_NOINTERFACE
        target[0] = this
        self.refs += 1
        return 0

    def add_ref(self, this):
        self.refs += 1
        return self.refs

    def release(self, this):
        self.refs = max(0, self.refs - 1)
        return self.refs

    def pre_delete(self, this, flags, item):
        if not flags & 0x80:  # TSF_DELETE_RECYCLE_IF_POSSIBLE
            self.blocked = True
            return -2147467259  # E_FAIL: veto permanent deletion
        return 0

    def post_delete(self, this, flags, item, result, created):
        self.result = result
        self.recycled = result >= 0 and bool(created)
        return 0


def recycle(path):
    ole, shell = c.WinDLL("ole32"), c.WinDLL("shell32")
    ole.CoInitializeEx.argtypes = (P, w.DWORD)
    ole.CoInitializeEx.restype = H
    ole.CoCreateInstance.argtypes = (P, P, w.DWORD, P, c.POINTER(P))
    ole.CoCreateInstance.restype = H
    ole.CoUninitialize.argtypes = ()
    ole.CoUninitialize.restype = None
    shell.SHCreateItemFromParsingName.argtypes = (w.LPCWSTR, P, P, c.POINTER(P))
    shell.SHCreateItemFromParsingName.restype = H
    initialized = ole.CoInitializeEx(None, 2)  # STA; balance S_OK and S_FALSE.
    if initialized < 0 and initialized != -2147417850:  # RPC_E_CHANGED_MODE
        checked(initialized)
    operation, item = P(), P()
    sink = Sink()
    try:
        checked(
            ole.CoCreateInstance(
                c.byref(FILE_OPERATION),
                None,
                1,
                c.byref(I_OPERATION),
                c.byref(operation),
            )
        )
        # RECYCLEONDELETE, ADDUNDORECORD, EARLYFAILURE, SILENT, NOCONFIRMATION, NOERRORUI.
        checked(
            method(operation, 5, H, w.DWORD)(operation, 0x20080000 | 0x00100000 | 0x414)
        )
        checked(
            shell.SHCreateItemFromParsingName(
                str(path), None, c.byref(I_ITEM), c.byref(item)
            )
        )
        checked(method(operation, 18, H, P, P)(operation, item, sink.pointer))
        checked(method(operation, 21, H)(operation))
        aborted = w.BOOL()
        checked(
            method(operation, 22, H, c.POINTER(w.BOOL))(operation, c.byref(aborted))
        )
        if aborted.value or sink.blocked or not sink.recycled:
            raise OSError("Working copy could not be moved to the Recycle Bin")
    finally:
        if item:
            method(item, 2, w.ULONG)(item)
        if operation:
            method(operation, 2, w.ULONG)(operation)
        if initialized >= 0:
            ole.CoUninitialize()
