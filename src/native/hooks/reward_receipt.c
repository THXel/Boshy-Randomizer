/* Synchronous write-ahead receipt. Loaded by the existing in-process DLL.
 * No game state is changed unless durable receipt publication succeeds. */
API(H, CreateFileA, (S, U, U, H, U, U, H));
API(I, ReadFile, (H, H, U, U *, H));
API(I, WriteFile, (H, H, U, U *, H));
API(I, FlushFileBuffers, (H));
API(I, CloseHandle, (H));
API(I, MoveFileExA, (S, S, U));
API(U, GetLastError, (void));
static I receipt_init(void) {
    if (CreateFileA && ReadFile && WriteFile && FlushFileBuffers && CloseHandle && MoveFileExA &&
        GetLastError)
        return 1;
    library = *(void **)0x45314c;
    symbol = *(void **)0x453128;
    H k = library("kernel32.dll");
    if (!k)
        return 0;
    GET(k, CreateFileA);
    GET(k, ReadFile);
    GET(k, WriteFile);
    GET(k, FlushFileBuffers);
    GET(k, CloseHandle);
    GET(k, MoveFileExA);
    GET(k, GetLastError);
    return 1;
}
static I hexchar(char c) {
    return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
}
static I samebytes(const unsigned char *a, const unsigned char *b, U n) {
    for (U j = 0; j < n; j++)
        if (a[j] != b[j])
            return 0;
    return 1;
}
I RewardCommit(S session, S key) {
    if (!receipt_init())
        return 0;
    for (U j = 0; j < 32; j++)
        if (!hexchar(session[j]))
            return 0;
    if (session[32] || (key[0] != 'i' && key[0] != 'l') || key[5])
        return 0;
    for (U j = 1; j < 5; j++)
        if (!hexchar(key[j]))
            return 0;
    unsigned char record[48] = {0};
    record[0] = 'B';
    record[1] = 'R';
    record[2] = 'W';
    record[3] = '1';
    for (U j = 0; j < 32; j++)
        record[4 + j] = session[j];
    for (U j = 0; j < 5; j++)
        record[36 + j] = key[j];
    U hash = 2166136261u;
    for (U j = 0; j < 44; j++)
        hash = (hash ^ record[j]) * 16777619u;
    for (U j = 0; j < 4; j++)
        record[44 + j] = (hash >> (8 * j)) & 255;
    char path[96] = {0}, temp[100] = {0};
    S prefix = "..\\native-runs\\", suffix = "\\rewards\\";
    U n = 0;
    for (U j = 0; prefix[j]; j++)
        path[n++] = prefix[j];
    for (U j = 0; j < 32; j++)
        path[n++] = session[j];
    for (U j = 0; suffix[j]; j++)
        path[n++] = suffix[j];
    for (U j = 0; j < 5; j++)
        path[n++] = key[j];
    path[n++] = '.';
    path[n++] = 'w';
    path[n++] = 'a';
    path[n++] = 'l';
    H existing = CreateFileA(path, 0x80000000, 1, 0, 3, 0, 0);
    if (existing != (H)-1) {
        unsigned char raw[49];
        U got = 0;
        I ok = ReadFile(existing, raw, 49, &got, 0);
        I closed = CloseHandle(existing);
        return ok && closed && got == 48 && samebytes(raw, record, 48);
    }
    if (GetLastError() != 2)
        return 0;
    for (U j = 0; j < n; j++)
        temp[j] = path[j];
    temp[n++] = '.';
    temp[n++] = 't';
    temp[n++] = 'm';
    temp[n++] = 'p';
    H f = CreateFileA(temp, 0x40000000, 0, 0, 2, 0x80000000, 0);
    if (f == (H)-1)
        return 0;
    U written = 0;
    I ok = WriteFile(f, record, 48, &written, 0) && written == 48;
    if (ok)
        ok = FlushFileBuffers(f);
    I closed = CloseHandle(f);
    if (!ok || !closed)
        return 0;
    /* No replacement: one permanent receipt per source, one game writer per run. */
    return MoveFileExA(temp, path, 8) != 0;
}
