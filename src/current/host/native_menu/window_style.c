/* Change decorations only on the explicitly named private Boshy test process.
 * No process-memory access, input injection, desktop mode change or termination.
 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdlib.h>
#include <errno.h>

static const char *expected;
static HWND target;
static int matches;

static BOOL CALLBACK find_window(HWND window, LPARAM unused) {
    (void)unused;
    char title[128], image[32768];
    DWORD pid, length = sizeof(image);
    if (!IsWindowVisible(window) || GetWindow(window, GW_OWNER)) return TRUE;
    if (!GetWindowTextA(window, title, sizeof(title)) ||
        strcmp(title, "I Wanna Be The Boshy")) return TRUE;
    GetWindowThreadProcessId(window, &pid);
    HANDLE process = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
    if (!process) return TRUE;
    BOOL ok = QueryFullProcessImageNameA(process, 0, image, &length);
    CloseHandle(process);
    if (ok && !lstrcmpiA(image, expected)) { target = window; matches++; }
    return TRUE;
}

int main(int argc, char **argv) {
    const char *prefix = "C:\\BoshySceneTests\\rebuilt-menu-";
    if (argc != 7 || strncmp(argv[1], prefix, strlen(prefix)) ||
        strstr(argv[1], "..") || (strcmp(argv[2], "borderless") && strcmp(argv[2], "restore"))) return 2;
    long geometry[4];
    for (int i = 0; i < 4; i++) {
        char *end; errno = 0;
        geometry[i] = strtol(argv[i + 3], &end, 10);
        if (errno || *end || geometry[i] < -32768 || geometry[i] > 32768 ||
            (i >= 2 && geometry[i] <= 0)) return 8;
    }
    expected = argv[1];
    EnumWindows(find_window, 0);
    if (matches != 1) return 3;
    LONG style = GetWindowLongA(target, GWL_STYLE);
    LONG ex = GetWindowLongA(target, GWL_EXSTYLE);
    const char *key = "BoshyRandomizerOriginalStyle";
    const char *exkey = "BoshyRandomizerOriginalExStyle";
    if (!strcmp(argv[2], "borderless")) {
        if (!GetPropA(target, key)) {
            if (!SetPropA(target, key, (HANDLE)(uintptr_t)((uint32_t)style + 1)) ||
                !SetPropA(target, exkey, (HANDLE)(uintptr_t)((uint32_t)ex + 1))) return 4;
        }
        style &= ~(WS_CAPTION | WS_THICKFRAME);
        ex &= ~(WS_EX_WINDOWEDGE | WS_EX_CLIENTEDGE | WS_EX_DLGMODALFRAME);
    } else {
        HANDLE saved = GetPropA(target, key), savedex = GetPropA(target, exkey);
        if (saved && savedex) {
            style = (LONG)((uintptr_t)saved - 1);
            ex = (LONG)((uintptr_t)savedex - 1);
            RemovePropA(target, key); RemovePropA(target, exkey);
        }
    }
    SetLastError(0);
    SetWindowLongA(target, GWL_STYLE, style);
    if (GetLastError()) return 5;
    SetLastError(0);
    SetWindowLongA(target, GWL_EXSTYLE, ex);
    if (GetLastError()) return 6;
    RECT rect = {0, 0, geometry[2], geometry[3]};
    if (!AdjustWindowRectEx(&rect, style, GetMenu(target) != NULL, ex)) return 9;
    if (!SetWindowPos(target, NULL, geometry[0], geometry[1],
                     rect.right - rect.left, rect.bottom - rect.top,
                     SWP_FRAMECHANGED | SWP_NOZORDER | SWP_NOACTIVATE)) return 7;
    puts("Window decoration updated");
    return 0;
}
