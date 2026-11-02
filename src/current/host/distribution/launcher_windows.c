/* One user-facing application entry point. The private runtime stays local. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <wchar.h>
#include <stdlib.h>

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, LPWSTR args, int show) {
    (void)instance; (void)previous; (void)args; (void)show;
    wchar_t root[32768], python[32768], command[65536];
    DWORD n = GetModuleFileNameW(NULL, root, 32768);
    if (!n || n >= 32768) return 2;
    wchar_t *slash = wcsrchr(root, L'\\');
    if (!slash) return 2;
    *slash = 0;
    if (swprintf(python, 32768, L"%ls\\maintenance\\runtime\\pythonw.exe", root) < 0 ||
        swprintf(command, 65536, L"\"%ls\" -B -X utf8 \"%ls\\maintenance\\app\\distribution\\dispatch_windows.py\"", python, root) < 0) return 2;
    STARTUPINFOW startup = {0}; startup.cb = sizeof(startup);
    PROCESS_INFORMATION process = {0};
    if (!CreateProcessW(python, command, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, root, &startup, &process)) {
        MessageBoxW(NULL, L"Boshy Randomizer could not start its application runtime. Please repair the installation.", L"Boshy Randomizer", MB_OK | MB_ICONERROR);
        return 3;
    }
    CloseHandle(process.hThread);
    WaitForSingleObject(process.hProcess, INFINITE);
    DWORD code = 1;
    GetExitCodeProcess(process.hProcess, &code);
    CloseHandle(process.hProcess);
    return (int)code;
}
