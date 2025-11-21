def rc4_crypt(key: bytes, data: bytes) -> bytes:
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) & 0xFF
        S[i], S[j] = S[j], S[i]
    i = j = 0
    out = bytearray()
    for b in data:
        i = (i + 1) & 0xFF
        j = (j + S[i]) & 0xFF
        S[i], S[j] = S[j], S[i]
        out.append(b ^ S[(S[i] + S[j]) & 0xFF])
    return bytes(out)
def decrypt_save(path, key):
    with open(path, "rb") as f:
        data = f.read()
    return rc4_crypt(key, data).decode("latin-1", errors="ignore")
def encrypt_save(text, path, key):
    data = text.encode("latin-1", errors="ignore")
    enc = rc4_crypt(key, data)
    with open(path, "wb") as f:
        f.write(enc)
