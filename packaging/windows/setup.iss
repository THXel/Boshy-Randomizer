; Build from the verified portable folder, using Inno Setup 7.
#ifndef PackageDir
  #error PackageDir must point to the verified BoshyRandomizer portable folder
#endif
#ifndef OutputDir
  #define OutputDir "dist"
#endif
#ifndef Version
  #define Version "2026.10.18"
#endif
[Setup]
AppId={{941C62AA-6EA4-4DE7-86C9-5C056762A805}
AppName=Boshy Randomizer
AppVersion={#Version} Windows Preview
AppPublisher=THXel
AppPublisherURL=https://github.com/THXel/Boshy-Randomizer
AppSupportURL=https://github.com/THXel/Boshy-Randomizer/issues
DefaultDirName={localappdata}\Programs\Boshy Randomizer
DefaultGroupName=Boshy Randomizer
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
MinVersion=10.0.17763
OutputDir={#OutputDir}
OutputBaseFilename=BoshyRandomizer-{#Version}-Windows-Setup-x64
SetupIconFile=..\..\Custom\rando_icon.ico
UninstallDisplayIcon={app}\BoshyRandomizer.ico
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
UninstallDisplayName=Boshy Randomizer
InfoBeforeFile=before.txt
[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "de"; MessagesFile: "compiler:Languages\German.isl"
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "ja"; MessagesFile: "compiler:Languages\Japanese.isl"
[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
[Files]
Source: "{#PackageDir}\runtime\*"; DestDir: "{app}\runtime"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PackageDir}\app\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\Custom\rando_icon.ico"; DestDir: "{app}"; DestName: "BoshyRandomizer.ico"; Flags: ignoreversion
[Icons]
Name: "{autoprograms}\Boshy Randomizer"; Filename: "{app}\runtime\pythonw.exe"; Parameters: "-B -X utf8 ""{app}\app\windows_entry.py"""; WorkingDir: "{app}"; IconFilename: "{app}\BoshyRandomizer.ico"
Name: "{autodesktop}\Boshy Randomizer"; Filename: "{app}\runtime\pythonw.exe"; Parameters: "-B -X utf8 ""{app}\app\windows_entry.py"""; WorkingDir: "{app}"; IconFilename: "{app}\BoshyRandomizer.ico"; Tasks: desktopicon
[Run]
Filename: "{app}\runtime\pythonw.exe"; Parameters: "-B -X utf8 ""{app}\app\windows_entry.py"""; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,Boshy Randomizer}"; Flags: nowait postinstall skipifsilent
; Intentionally no UninstallDelete: user game data and saves are outside {app}.
[Code]
function NextButtonClick(CurPageID: Integer): Boolean;
var Target, DataPath: String;
begin
  Result := True;
  if CurPageID = wpSelectDir then begin
    Target := Lowercase(AddBackslash(ExpandFileName(WizardDirValue)));
    DataPath := Lowercase(AddBackslash(ExpandConstant('{localappdata}\BoshyRandomizer')));
    if (Pos(DataPath, Target) = 1) or (Pos(Target, DataPath) = 1) then begin
      MsgBox(CustomMessage('SeparateData'), mbError, MB_OK);
      Result := False;
    end;
  end;
end;
[CustomMessages]
en.SeparateData=Choose a separate application folder. Your game and saved runs must stay outside the installation folder.
de.SeparateData=Wähle einen separaten Programmordner. Das Spiel und deine Spielstände müssen außerhalb des Installationsordners bleiben.
ru.SeparateData=Выберите отдельную папку программы. Игра и сохранения должны находиться вне папки установки.
es.SeparateData=Elige una carpeta separada para la aplicación. El juego y las partidas deben quedar fuera de la carpeta de instalación.
ja.SeparateData=アプリ専用のフォルダーを選んでください。ゲームとセーブデータはインストール先の外に保存します。
