; ============================================================
; Boshy Randomizer - Full Installer (English)
; ============================================================

!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "FileFunc.nsh"

Var BOSHZIP

Name "Boshy Randomizer"
OutFile "BoshyRandomizerSetup.exe"

InstallDir "$PROGRAMFILES\Boshy Randomizer"
RequestExecutionLevel highest

; ---------- MUI / GUI Setup ----------
!define MUI_ABORTWARNING

; Optional: custom icons (if available)
!define MUI_ICON "Custom\install_icon.ico"
!define MUI_UNICON "Custom\install_icon.ico"

; Welcome / Finish page banner bitmap
!define MUI_WELCOMEFINISHPAGE_BITMAP "Custom\boshy_banner.bmp"

; Wizard pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "Custom\License.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

; Finish page with:
; - Run Boshy Randomizer checkbox
; - OPTIONAL: "Create desktop shortcut" checkbox
!define MUI_FINISHPAGE_RUN "$INSTDIR\Boshy Randomizer.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Start Boshy Randomizer now"

!define MUI_FINISHPAGE_SHOWREADME
!define MUI_FINISHPAGE_SHOWREADME_TEXT "Create a desktop shortcut"
!define MUI_FINISHPAGE_SHOWREADME_FUNCTION CreateDesktopShortcut

!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

ShowInstDetails show
ShowUninstDetails show

; ============================================================
; MAIN INSTALL SECTION
; ============================================================
Section "Install"

  SetOutPath "$INSTDIR"

  ; Copy ALL files from your project folder into the install dir.
  File /r "*.*"

  ; --- Create uninstaller ---
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; --- Add Uninstall entry (Programs & Features) ---
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BoshyRandomizer" "DisplayName" "Boshy Randomizer"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BoshyRandomizer" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BoshyRandomizer" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BoshyRandomizer" "DisplayVersion" "1.0.0"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BoshyRandomizer" "Publisher" "THXel"

  ; --- Create Start Menu shortcuts ---
  CreateDirectory "$SMPROGRAMS\Boshy Randomizer"
  CreateShortCut "$SMPROGRAMS\Boshy Randomizer\Boshy Randomizer.lnk" \
                 "$INSTDIR\Boshy Randomizer.exe" \
                 "" \
                 "$INSTDIR\Custom\rando_icon.ico"

  CreateShortCut "$SMPROGRAMS\Boshy Randomizer\Uninstall Boshy Randomizer.lnk" \
                 "$INSTDIR\Uninstall.exe"

  ; --- 1) Ask user for Boshy ZIP, extract to IWBTB, validate EXE ---
  Call AskAndExtractBoshy

  ; --- 2) Check & auto-install Python if needed ---
  Call CheckAndInstallPython

  ; --- 3) Install pip and required Python modules ---
  Call InstallPipAndModules

  ; --- 4) Install custom font ---
  Call InstallBoshyFont

SectionEnd

; ============================================================
; UNINSTALL SECTION
; ============================================================
Section "Uninstall"

  ; Remove Start Menu shortcuts
  Delete "$SMPROGRAMS\Boshy Randomizer\Boshy Randomizer.lnk"
  Delete "$SMPROGRAMS\Boshy Randomizer\Uninstall Boshy Randomizer.lnk"
  RMDir  "$SMPROGRAMS\Boshy Randomizer"

  ; Remove desktop shortcut (if it exists)
  Delete "$DESKTOP\Boshy Randomizer.lnk"

  ; Remove uninstall entry + files
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\BoshyRandomizer"
  RMDir /r "$INSTDIR"

SectionEnd

; ============================================================
; FUNCTION: Finish-page checkbox -> create desktop shortcut
; ============================================================
Function CreateDesktopShortcut
  CreateShortCut "$DESKTOP\Boshy Randomizer.lnk" \
                 "$INSTDIR\Boshy Randomizer.exe" \
                 "" \
                 "$INSTDIR\Custom\rando_icon.ico"
FunctionEnd

; ============================================================
; FUNCTION: Ask for Boshy ZIP (native NSIS dialog), extract to IWBTB, validate EXE
; ============================================================
Function AskAndExtractBoshy

  ; If the game is already present, ask whether to re-import
  ${If} ${FileExists} "$INSTDIR\IWBTB\I Wanna Be The Boshy.exe"
    MessageBox MB_YESNO "An existing 'I Wanna Be The Boshy.exe' was found in the IWBTB folder.$\r$\n$\r$\nDo you want to re-import the game from a ZIP file?" IDNO NoReimport
  ${EndIf}

  ; Info box + open Grynsoft page
  MessageBox MB_ICONINFORMATION|MB_OK \
    "To use this Randomizer you need the original game 'I Wanna Be The Boshy'.$\r$\n$\r$\nAfter clicking OK, the official Grynsoft website will open. Then you can select your downloaded ZIP file."

  Exec '"$WINDIR\explorer.exe" "https://grynsoft.com/old-games"'

  ; Native NSIS file selection dialog (no filter, user should pick the ZIP)
  DetailPrint "Selecting Boshy ZIP..."
  nsDialogs::SelectFileDialog "" ""
  Pop $BOSHZIP

  ; If no file was selected, abort installation
  StrCmp $BOSHZIP "" 0 +3
    MessageBox MB_ICONSTOP "No ZIP file selected. Installation cannot continue without the game files."
    Abort

  DetailPrint "Selected Boshy ZIP: $BOSHZIP"

  ; Prepare temporary extraction folder
  StrCpy $1 "$INSTDIR\IWBTB_temp_extract"
  ${If} ${FileExists} "$1"
    RMDir /r "$1"
  ${EndIf}
  CreateDirectory "$1"

  ; Extract ZIP using PowerShell Expand-Archive (fixed quoting)
  DetailPrint "Extracting Boshy ZIP..."
  nsExec::ExecToStack 'powershell -NoProfile -Command "Expand-Archive -LiteralPath \"$BOSHZIP\" -DestinationPath \"$1\" -Force"'
  Pop $0
  DetailPrint "Expand-Archive exit code: $0"

  ; Validate presence of EXE (directly or in IWBTB\)
  ${IfNot} ${FileExists} "$1\I Wanna Be The Boshy.exe"
    ${IfNot} ${FileExists} "$1\IWBTB\I Wanna Be The Boshy.exe"
      MessageBox MB_ICONSTOP "The selected ZIP does not contain 'I Wanna Be The Boshy.exe'. Please make sure you downloaded the original archive from Grynsoft (it should contain an IWBTB folder with the EXE inside)."
      RMDir /r "$1"
      Abort
    ${EndIf}
  ${EndIf}

  DetailPrint "Valid Boshy ZIP detected."

  ; Prepare final IWBTB folder
  CreateDirectory "$INSTDIR\IWBTB"

  ; Handle possible nested IWBTB folder
  ${If} ${FileExists} "$1\IWBTB\I Wanna Be The Boshy.exe"
    DetailPrint "Found nested IWBTB folder – flattening..."
    CopyFiles /SILENT "$1\IWBTB\*.*" "$INSTDIR\IWBTB\"
  ${Else}
    CopyFiles /SILENT "$1\*.*" "$INSTDIR\IWBTB\"
  ${EndIf}

  ; Clean up temp folder
  RMDir /r "$1"

  ; Final check
  ${IfNot} ${FileExists} "$INSTDIR\IWBTB\I Wanna Be The Boshy.exe"
    MessageBox MB_ICONSTOP "Something went wrong: 'I Wanna Be The Boshy.exe' was not found after extraction."
    Abort
  ${EndIf}

  DetailPrint "Game extracted successfully."
  Return

NoReimport:
  DetailPrint "Existing I Wanna Be The Boshy.exe found – skipping ZIP import."
  Return

FunctionEnd

; ============================================================
; FUNCTION: Check & auto-install Python
; ============================================================
Function CheckAndInstallPython

  DetailPrint "Checking for Python..."
  nsExec::ExecToStack 'cmd /c "python --version"'
  Pop $1  ; exit code
  Pop $2  ; output

  ${If} $1 = 0
    DetailPrint "Python detected: $2"
    Return
  ${EndIf}

  MessageBox MB_ICONINFORMATION|MB_OK \
    "Python 3.x was not found on this system.$\r$\n$\r$\nThe installer will now download and install Python 3.12.3 from python.org."

  StrCpy $3 "$TEMP\python-3.12.3-amd64.exe"
  DetailPrint "Downloading Python installer to $3..."

  NSISdl::download "https://www.python.org/ftp/python/3.12.3/python-3.12.3-amd64.exe" "$3"
  Pop $0
  ${If} $0 != "success"
    MessageBox MB_ICONSTOP "Failed to download the Python installer. Please install Python 3.x manually from python.org and re-run this installer."
    Abort
  ${EndIf}

  DetailPrint "Running Python installer..."
  ExecWait '"$3" /quiet PrependPath=1'

  ; Check again
  nsExec::ExecToStack 'cmd /c "python --version"'
  Pop $1
  Pop $2

  ${If} $1 != 0
    MessageBox MB_ICONSTOP "Python installation appears to have failed. Please install Python 3.x manually from python.org and re-run this installer."
    Abort
  ${EndIf}

  DetailPrint "Python installation completed: $2"

FunctionEnd

; ============================================================
; FUNCTION: Install pip + Python modules
; ============================================================
Function InstallPipAndModules

  DetailPrint "Checking pip..."
  nsExec::ExecToStack 'cmd /c "python -m pip --version"'
  Pop $1
  Pop $2

  ${If} $1 != 0
    DetailPrint "pip not found – trying ensurepip..."
    nsExec::ExecToStack 'cmd /c "python -m ensurepip --upgrade"'
    Pop $1
    Pop $2

    nsExec::ExecToStack 'cmd /c "python -m pip --version"'
    Pop $1
    Pop $2

    ${If} $1 != 0
      DetailPrint "ensurepip failed – trying get-pip.py (internet required)..."
      nsExec::ExecToStack 'powershell -NoProfile -Command "(New-Object Net.WebClient).DownloadFile(''https://bootstrap.pypa.io/get-pip.py'',''$TEMP\get-pip.py'')"'
      Pop $0
      nsExec::ExecToStack 'cmd /c "python ""%TEMP%\get-pip.py"""'
      Pop $0
      Delete "$TEMP\get-pip.py"

      nsExec::ExecToStack 'cmd /c "python -m pip --version"'
      Pop $1
      Pop $2
      ${If} $1 != 0
        MessageBox MB_ICONSTOP "pip could not be installed. Please check your internet connection or install pip manually."
        Abort
      ${EndIf}
    ${EndIf}
  ${EndIf}

  DetailPrint "pip ready: $2"
  DetailPrint "Installing required Python modules (this may take a while)..."

  nsExec::ExecToStack 'cmd /c "python -m pip install --upgrade PySide6 keyboard pyautogui pillow numpy pygetwindow pymem twitchio"'
  Pop $1
  Pop $2

  ${If} $1 != 0
    MessageBox MB_ICONEXCLAMATION "Some Python modules may not have installed correctly. Please review the output when running the Randomizer."
  ${Else}
    DetailPrint "All required Python modules installed/updated."
  ${EndIf}

FunctionEnd

; ============================================================
; FUNCTION: Install font "its-boshy-time.ttf" for current user
; ============================================================
Function InstallBoshyFont

  DetailPrint "Installing custom font 'its-boshy-time.ttf'..."

  StrCpy $0 "$INSTDIR\Custom\fonts\its-boshy-time.ttf"
  ${IfNot} ${FileExists} "$0"
    StrCpy $0 "$INSTDIR\Custom\its-boshy-time.ttf"
  ${EndIf}

  ${IfNot} ${FileExists} "$0"
    DetailPrint "Font file not found in Custom/fonts or Custom – skipping font installation."
    Return
  ${EndIf}

  ReadEnvStr $1 "LOCALAPPDATA"
  StrCpy $2 "$1\Microsoft\Windows\Fonts"
  CreateDirectory "$2"

  CopyFiles /SILENT "$0" "$2\its-boshy-time.ttf"

  ; Register font for current user
  WriteRegStr HKCU "Software\Microsoft\Windows NT\CurrentVersion\Fonts" "its-boshy-time (TrueType)" "its-boshy-time.ttf"

  DetailPrint "Font installed for current user (a logoff/logon may be required in some apps)."

FunctionEnd
