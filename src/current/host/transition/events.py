"""Small typed builders for the recovered MMF2 event format (original ANSI input)."""
import struct


def parameter(kind, payload):
    return struct.pack('<HH', len(payload) + 4, kind) + payload


def integer(value):
    return struct.pack('<hhHi', -1, 0, 10, value)


def string(value):
    data = value.encode('ascii') + b'\0'
    data += b'\0' * (len(data) % 2)
    return struct.pack('<hhH', -1, 3, len(data) + 6) + data


def expression(tokens, kind=22, comparison=0):
    return parameter(kind, struct.pack('<H', comparison) + tokens + bytes(4))


def ini_value(group, key, default=0, oi=312):
    separator = struct.pack('<hhH', -1, -3, 6)
    close = struct.pack('<hhH', -1, -2, 6)
    return (struct.pack('<hhHHH', 33, 88, 10, oi, 0) + string(group)
            + separator + string(key) + separator + integer(default) + close)


def action(kind, code, oi, params):
    body = b''.join(params)
    return struct.pack('<HhhHHHBB', 14 + len(body), kind, code, oi, 0, 0, len(params), 0) + body


def compare_ini(group, key, value, comparison, identifier, oi=312):
    params = expression(ini_value(group, key, oi=oi)) + expression(integer(value), 23, comparison)
    return struct.pack('<HhhHHHBBH', 16 + len(params), -1, -3, 0, 0, 0x20, 2, 0, identifier) + params


def global_value(index, value):
    return action(-1, 3, 0, [parameter(49, struct.pack('<IH', index, 0)), expression(integer(value))])


def set_ini(group, key, value, oi=312):
    return action(33, 94, oi, [expression(string(group), 45), expression(string(key), 45),
                              expression(integer(0)), expression(integer(value))])


def commands(row):
    offset = 14
    result = []
    for index in range(row[2] + row[3]):
        size, kind, code, oi = struct.unpack_from('<HhhH', row, offset)
        assert size >= 14 and offset + size <= len(row)
        result.append((index < row[2], kind, code, oi, row[offset:offset + size]))
        offset += size
    assert offset == len(row)
    return result


def event(template, conditions, actions):
    body = b''.join(conditions + actions)
    head = bytearray(template[:14])
    struct.pack_into('<hBB', head, 0, -14 - len(body), len(conditions), len(actions))
    return bytes(head) + body
