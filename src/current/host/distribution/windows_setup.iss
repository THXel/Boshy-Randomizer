; Boshy Randomizer installer. Accepts a separately verified application payload.
#ifndef Payload
  #error Payload must name the staged application package
#endif
#ifndef Launcher
  #error Launcher must name the compiled application starter
#endif
#ifndef Output
  #error Output must name the installer output directory
#endif
#ifndef Version
  #error Version is required
#endif
[Setup]
AppId={{D399DF48-D962-48EA-A720-27631CFEA57B}
AppName=Boshy Randomizer
AppVersion={#Version}
AppPublisher=THXel
DefaultDirName={localappdata}\Programs\Boshy Randomizer
DefaultGroupName=Boshy Randomizer
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
WizardStyle=modern
DisableProgramGroupPage=yes
OutputDir={#Output}
OutputBaseFilename=BoshyRandomizer-Setup-{#Version}
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\BoshyRandomizer.exe
CloseApplications=no
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"

[CustomMessages]
english.RemoveTitle=Uninstall Boshy Randomizer
german.RemoveTitle=Boshy Randomizer deinstallieren
spanish.RemoveTitle=Desinstalar Boshy Randomizer
russian.RemoveTitle=Удаление Boshy Randomizer
japanese.RemoveTitle=Boshy Randomizerのアンインストール
english.RemoveData=Also delete saves and settings
german.RemoveData=Spielstände und Einstellungen ebenfalls löschen
spanish.RemoveData=Eliminar también partidas y ajustes
russian.RemoveData=Также удалить сохранения и настройки
japanese.RemoveData=セーブデータと設定も削除する
english.RemoveHint=Your saves and settings are kept unless you select the checkbox below. Deleting them cannot be undone. The original game is not affected.
german.RemoveHint=Ohne Häkchen bleiben deine Spielstände und Einstellungen erhalten. Ihre Löschung kann nicht rückgängig gemacht werden. Das Originalspiel bleibt unverändert.
spanish.RemoveHint=Sin marcar la casilla se conservan tus partidas y ajustes. Su eliminación es irreversible. El juego original no se modifica.
russian.RemoveHint=Без галочки сохранения и настройки останутся. Их удаление необратимо. Оригинальная игра не изменяется.
japanese.RemoveHint=チェックしなければセーブデータと設定は残ります。削除は取り消せません。元のゲームは変更されません。
english.RemoveContinue=Uninstall
german.RemoveContinue=Deinstallieren
spanish.RemoveContinue=Desinstalar
russian.RemoveContinue=Удалить
japanese.RemoveContinue=アンインストール

english.SourceTitle=Original Boshy game
english.SourceDescription=Select your original game. Setup copies and patches it without changing your files.
english.SourceKind=Where is your original Boshy game?
english.ZipChoice=ZIP archive
english.FolderChoice=Extracted game folder
english.SourceZip=Select the original Boshy ZIP archive.
english.SourceFolder=Select the folder containing the original Boshy game.
english.MissingSource=Please select an existing original Boshy ZIP or folder.
english.InstallError=The game could not be prepared. Your active version has been kept. Close Boshy Randomizer if it is running, and check that you selected the unmodified original. Details:
english.RemoveError=The game files could not be removed. Close Boshy Randomizer and try again.
german.SourceTitle=Originales Boshy-Spiel
german.SourceDescription=Wähle dein Originalspiel. Setup kopiert und patcht es, ohne deine Dateien zu verändern.
german.SourceKind=Wo liegt dein originales Boshy-Spiel?
german.ZipChoice=ZIP-Archiv
german.FolderChoice=Entpackter Spielordner
german.SourceZip=Wähle das ZIP-Archiv des originalen Boshy-Spiels.
german.SourceFolder=Wähle den Ordner mit dem originalen Boshy-Spiel.
german.MissingSource=Bitte wähle ein vorhandenes Original-ZIP oder einen Spielordner.
german.InstallError=Das Spiel konnte nicht vorbereitet werden. Deine aktive Version bleibt erhalten. Schließe Boshy Randomizer, falls es läuft, und prüfe, ob du das unveränderte Original ausgewählt hast. Details:
german.RemoveError=Die Spieldateien konnten nicht entfernt werden. Schließe Boshy Randomizer und versuche es erneut.

german.ProgressTitle=Boshy Randomizer einrichten
english.ProgressTitle=Setting up Boshy Randomizer
german.ProgressHint=Fortschritt des aktuellen Arbeitsschritts.
english.ProgressHint=Progress of the current step.
german.Working=Wird bearbeitet …
english.Working=Working …
german.extracting=Installationsdateien werden entpackt …
english.extracting=Unpacking setup files …
german.waiting=Installation wird vorbereitet …
english.waiting=Preparing installation …
german.checking=Installationspaket wird geprüft …
english.checking=Checking setup files …
german.importing=Originalspiel wird geprüft und kopiert …
english.importing=Checking and copying the original game …
german.patching=Randomizer-Patch wird vorbereitet …
english.patching=Preparing the randomizer patch …
german.images=Spielgrafiken werden zusammengesetzt …
english.images=Rebuilding game graphics …
german.audio=Spielklänge werden zusammengesetzt …
english.audio=Rebuilding game sounds …
german.writing=Gepatchtes Spiel wird gespeichert …
english.writing=Saving the patched game …
german.copying=Programm und Musikpakete werden kopiert …
english.copying=Copying the application and music packs …
german.verifying=Installierte Dateien werden geprüft …
english.verifying=Verifying installed files …
german.activating=Neue Version wird aktiviert …
english.activating=Activating the new version …
german.removing=Installierte Spieldateien werden entfernt …
english.removing=Removing installed game files …
german.ready=Arbeitsschritt abgeschlossen
english.ready=Step completed
german.PhaseProgress=Fortschritt dieses Schritts:
english.PhaseProgress=Progress of this step:

english.Cancelling=Cancelling safely …
german.Cancelling=Wird sicher abgebrochen …
english.Cancelled=Installation cancelled. Your active version and saves have been kept. You can retry or close Setup.
german.Cancelled=Installation abgebrochen. Deine aktive Version und Spielstände bleiben erhalten. Du kannst erneut versuchen oder Setup schließen.
english.Finished=Boshy Randomizer was installed successfully. You can start the game now using the checkbox below, or later using its shortcut.
german.Finished=Boshy Randomizer wurde erfolgreich installiert. Du kannst das Spiel mit dem Häkchen unten jetzt starten oder später über die Verknüpfung öffnen.

spanish.SourceTitle=Juego original de Boshy
russian.SourceTitle=Оригинальная игра Boshy
japanese.SourceTitle=Boshyのオリジナルゲーム
spanish.SourceDescription=Selecciona el original. Se copiará y modificará sin cambiar tus archivos.
russian.SourceDescription=Выбери оригинал. Установщик создаст изменённую копию, не меняя исходные файлы.
japanese.SourceDescription=オリジナルを選択してください。元のファイルを変更せず、コピーにパッチを適用します。
spanish.SourceKind=¿Dónde está tu juego original de Boshy?
russian.SourceKind=Где находится оригинальная игра Boshy?
japanese.SourceKind=オリジナルゲームの場所を選択
spanish.ZipChoice=Archivo ZIP
russian.ZipChoice=ZIP-архив
japanese.ZipChoice=ZIPファイル
spanish.FolderChoice=Carpeta del juego extraído
russian.FolderChoice=Папка распакованной игры
japanese.FolderChoice=展開済みのゲームフォルダー
spanish.SourceZip=Selecciona el ZIP original de Boshy.
russian.SourceZip=Выбери ZIP-архив оригинальной игры.
japanese.SourceZip=オリジナルのZIPファイルを選択してください。
spanish.SourceFolder=Selecciona la carpeta del juego original.
russian.SourceFolder=Выбери папку оригинальной игры.
japanese.SourceFolder=オリジナルゲームのフォルダーを選択してください。
spanish.MissingSource=Selecciona un ZIP o una carpeta original que exista.
russian.MissingSource=Выбери существующий ZIP-архив или папку оригинала.
japanese.MissingSource=存在するZIPファイルまたはフォルダーを選択してください。
spanish.InstallError=No se pudo preparar el juego. La versión activa se conserva. Cierra el juego y selecciona el original sin modificar. Detalles:
russian.InstallError=Не удалось подготовить игру. Текущая версия сохранена. Закрой игру и выбери неизменённый оригинал. Подробности:
japanese.InstallError=ゲームを準備できませんでした。現在のバージョンは保持されています。ゲームを終了し、未改変のオリジナルを選択してください。詳細:
spanish.RemoveError=No se pudieron eliminar los archivos. Cierra el juego e inténtalo de nuevo.
russian.RemoveError=Не удалось удалить файлы. Закрой игру и повтори попытку.
japanese.RemoveError=ファイルを削除できませんでした。ゲームを終了して再試行してください。
spanish.ProgressTitle=Instalar Boshy Randomizer
russian.ProgressTitle=Установка Boshy Randomizer
japanese.ProgressTitle=Boshy Randomizerのセットアップ
spanish.ProgressHint=Progreso del paso actual.
russian.ProgressHint=Ход текущего этапа.
japanese.ProgressHint=現在の作業の進行状況
spanish.Working=Procesando …
russian.Working=Выполняется …
japanese.Working=処理中 …
spanish.extracting=Extrayendo archivos de instalación …
russian.extracting=Распаковка установочных файлов …
japanese.extracting=セットアップファイルを展開中 …
spanish.waiting=Preparando la instalación …
russian.waiting=Подготовка установки …
japanese.waiting=インストールを準備中 …
spanish.checking=Comprobando archivos de instalación …
russian.checking=Проверка установочных файлов …
japanese.checking=セットアップファイルを確認中 …
spanish.importing=Comprobando y copiando el juego original …
russian.importing=Проверка и копирование оригинальной игры …
japanese.importing=オリジナルゲームを確認・コピー中 …
spanish.patching=Preparando el parche …
russian.patching=Подготовка патча …
japanese.patching=パッチを準備中 …
spanish.images=Reconstruyendo gráficos del juego …
russian.images=Сборка графики игры …
japanese.images=ゲームの画像を構築中 …
spanish.audio=Reconstruyendo sonidos del juego …
russian.audio=Сборка звуков игры …
japanese.audio=ゲームの音声を構築中 …
spanish.writing=Guardando el juego modificado …
russian.writing=Сохранение изменённой игры …
japanese.writing=パッチ適用済みゲームを保存中 …
spanish.copying=Copiando el programa y la música …
russian.copying=Копирование программы и музыки …
japanese.copying=プログラムと音楽をコピー中 …
spanish.verifying=Verificando los archivos instalados …
russian.verifying=Проверка установленных файлов …
japanese.verifying=インストール済みファイルを確認中 …
spanish.activating=Activando la nueva versión …
russian.activating=Активация новой версии …
japanese.activating=新しいバージョンを有効化中 …
spanish.removing=Eliminando archivos del juego …
russian.removing=Удаление файлов игры …
japanese.removing=ゲームファイルを削除中 …
spanish.ready=Paso completado
russian.ready=Этап завершён
japanese.ready=作業完了
spanish.PhaseProgress=Progreso del paso:
russian.PhaseProgress=Ход этапа:
japanese.PhaseProgress=現在の作業:
spanish.Cancelling=Cancelando de forma segura …
russian.Cancelling=Безопасная отмена …
japanese.Cancelling=安全に中止しています …
spanish.Cancelled=Instalación cancelada. La versión activa y las partidas se conservan. Puedes reintentar o cerrar.
russian.Cancelled=Установка отменена. Текущая версия и сохранения сохранены. Можно повторить попытку или закрыть окно.
japanese.Cancelled=インストールを中止しました。現在のバージョンとセーブデータは保持されています。再試行するか終了できます。
spanish.Finished=Boshy Randomizer se ha instalado correctamente. Marca la casilla de abajo para jugar ahora o usa el acceso directo más tarde.
russian.Finished=Boshy Randomizer успешно установлен. Отметь флажок ниже, чтобы играть сейчас, или используй ярлык позже.
japanese.Finished=Boshy Randomizerのインストールが完了しました。下のチェックボックスで今すぐ起動するか、後でショートカットから起動できます。

german.committing=Vorbereitung wird abgeschlossen …
english.committing=Completing preparation …
spanish.committing=Finalizando la preparación …
russian.committing=Завершение подготовки …
japanese.committing=準備を完了しています …

[Tasks]
Name: desktopicon; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#Payload}\*"; DestDir: "{tmp}\payload"; Flags: dontcopy recursesubdirs createallsubdirs
Source: "{#Payload}\runtime\*"; DestDir: "{app}\maintenance\runtime"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#Payload}\app\*"; DestDir: "{app}\maintenance\app"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#Launcher}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Boshy Randomizer"; Filename: "{app}\BoshyRandomizer.exe"
Name: "{autodesktop}\Boshy Randomizer"; Filename: "{app}\BoshyRandomizer.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\BoshyRandomizer.exe"; Description: "{cm:LaunchProgram,Boshy Randomizer}"; Flags: nowait postinstall skipifsilent unchecked

[Code]
var
  SourceType: TInputOptionWizardPage;
  ZipPage: TInputFileWizardPage;
  FolderPage: TInputDirWizardPage;
  Extracted: Boolean;
  ProgressPage: TOutputProgressWizardPage;
  StopButton: TNewButton;
  CancelFile: String;
  PreparingWorker, StopRequested: Boolean;
  DeleteUserData: Boolean;

function EnableWindow(hWnd: HWND; bEnable: Boolean): Boolean;
  external 'EnableWindow@user32.dll stdcall';

function Quote(const S: String): String;
begin
  Result := '"' + S + '"';
end;

procedure RequestStop(Sender: TObject);
begin
  if PreparingWorker and not StopRequested then begin
    StopRequested := True;
    SaveStringToFile(CancelFile, 'cancel', False);
    StopButton.Enabled := False;
    StopButton.Caption := CustomMessage('Cancelling');
  end;
end;

procedure CancelButtonClick(CurPageID: Integer; var Cancel, Confirm: Boolean);
begin
  if PreparingWorker then begin
    RequestStop(nil);
    Cancel := False;
    Confirm := False;
  end;
end;

procedure InitializeWizard;
begin
  ProgressPage := CreateOutputProgressPage(CustomMessage('ProgressTitle'), CustomMessage('ProgressHint'));
  CancelFile := ExpandConstant('{tmp}\boshy-cancel');
  StopButton := TNewButton.Create(WizardForm);
  StopButton.Parent := ProgressPage.Surface;
  StopButton.Left := ScaleX(0);
  StopButton.Top := ScaleY(180);
  StopButton.Width := ScaleX(190);
  StopButton.Height := ScaleY(28);
  StopButton.Caption := SetupMessage(msgButtonCancel);
  StopButton.OnClick := @RequestStop;
  StopButton.Enabled := False;

  SourceType := CreateInputOptionPage(wpSelectDir, CustomMessage('SourceTitle'), CustomMessage('SourceDescription'), CustomMessage('SourceKind'), True, False);
  SourceType.Add(CustomMessage('ZipChoice'));
  SourceType.Add(CustomMessage('FolderChoice'));
  SourceType.SelectedValueIndex := 0;
  ZipPage := CreateInputFilePage(SourceType.ID, CustomMessage('SourceTitle'), CustomMessage('SourceDescription'), CustomMessage('SourceZip'));
  ZipPage.Add('ZIP:', '*.zip|*.zip', '.zip');
  FolderPage := CreateInputDirPage(ZipPage.ID, CustomMessage('SourceTitle'), CustomMessage('SourceDescription'), CustomMessage('SourceFolder'), False, '');
  FolderPage.Add('');
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := ((PageID = ZipPage.ID) and (SourceType.SelectedValueIndex <> 0)) or
    ((PageID = FolderPage.ID) and (SourceType.SelectedValueIndex <> 1));
end;

function OriginalSource: String;
begin
  Result := ExpandConstant('{param:ORIGINAL|}');
  if Result = '' then begin
    if SourceType.SelectedValueIndex = 0 then Result := ZipPage.Values[0]
    else Result := FolderPage.Values[0];
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var Source: String;
begin
  Result := True;
  if (CurPageID = ZipPage.ID) or (CurPageID = FolderPage.ID) then begin
    Source := OriginalSource;
    Result := FileExists(Source) or DirExists(Source);
    if not Result then MsgBox(CustomMessage('MissingSource'), mbError, MB_OK);
  end;
end;

procedure WorkerOutput(const S: String; const Error, FirstLine: Boolean);
var Current, Total, Percent, Separator: Integer; Caption, Detail, Rest, Stage: String;
    Bar: TNewProgressBar;
begin
  Log(S);
  if Error or (Pos('BOSHY_PROGRESS|', S) <> 1) then Exit;
  Rest := Copy(S, 16, Length(S));
  Separator := Pos('|', Rest);
  if Separator = 0 then Exit;
  Stage := Copy(Rest, 1, Separator - 1);
  Delete(Rest, 1, Separator);
  Separator := Pos('|', Rest);
  if Separator = 0 then Exit;
  Current := StrToIntDef(Copy(Rest, 1, Separator - 1), -1);
  Delete(Rest, 1, Separator);
  Total := StrToIntDef(Rest, -1);
  if (Current < 0) or (Total < Current) then Exit;
  if not IsUninstaller then begin
    { ExecAndLogOutput disables the wizard. The progress page hides all
      navigation; only our cooperative stop button may accept input. }
    if Stage = 'committing' then begin
      PreparingWorker := False;
      StopButton.Enabled := False;
      EnableWindow(WizardForm.Handle, False);
    end else if PreparingWorker then
      EnableWindow(WizardForm.Handle, True);
  end;
  Caption := CustomMessage(Stage);
  Detail := CustomMessage('Working');
  if Total > 0 then begin
    Percent := Round(100.0 * Current / Total);
    Detail := CustomMessage('PhaseProgress') + ' ' + IntToStr(Percent) + ' %';
  end;
  if IsUninstaller then begin
    Bar := UninstallProgressForm.ProgressBar;
    UninstallProgressForm.StatusLabel.Caption := Caption + #13#10 + Detail;
  end else begin
    Bar := ProgressPage.ProgressBar;
    ProgressPage.SetText(Caption, Detail);
  end;
  Bar.Visible := True;
  if Total = 0 then Bar.Style := npbstMarquee
  else begin
    Bar.Style := npbstNormal;
    Bar.Min := 0;
    Bar.Max := Total;
    Bar.Position := Current;
  end;
end;

function Worker(Action, RuntimeRoot, Extra, Report: String): Boolean;
var Code: Integer;
begin
  if not IsUninstaller then begin
    PreparingWorker := Action = 'prepare';
    StopRequested := False;
    DeleteFile(CancelFile);
    StopButton.Visible := PreparingWorker;
    StopButton.Enabled := PreparingWorker;
    StopButton.Caption := SetupMessage(msgButtonCancel);
    if PreparingWorker then Extra := Extra + ' --cancel-file ' + Quote(CancelFile);
    ProgressPage.SetText(CustomMessage('waiting'), CustomMessage('Working'));
    ProgressPage.ProgressBar.Style := npbstMarquee;
    ProgressPage.ProgressBar.Visible := True;
    ProgressPage.Show;
  end;
  try
    Result := ExecAndLogOutput(RuntimeRoot + '\runtime\python.exe',
      '-u -B -X utf8 ' + Quote(RuntimeRoot + '\app\distribution\setup_worker.py') +
      ' ' + Action + ' --root ' + Quote(ExpandConstant('{app}')) +
      ' --report ' + Quote(Report) + ' --language ' + Quote(ExpandConstant('{language}')) + ' ' + Extra,
      RuntimeRoot, SW_SHOWNORMAL, ewWaitUntilTerminated, Code, @WorkerOutput);
    Result := Result and (Code = 0);
  finally
    PreparingWorker := False;
    if not IsUninstaller then ProgressPage.Hide;
  end;
end;

function FailureMessage(const Report: String): String;
var Detail: String;
begin
  Detail := GetIniString('Failure', 'Message', '', Report + '.ini');
  if StopRequested then begin
    Result := CustomMessage('Cancelled');
    Exit;
  end;
  Result := CustomMessage('InstallError');
  if Detail <> '' then Result := Detail + #13#10 + #13#10 + Result;
  Result := Result + #13#10 + Report;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var Source, Report: String;
begin
  Result := '';
  Source := OriginalSource;
  if not (FileExists(Source) or DirExists(Source)) then begin
    Result := CustomMessage('MissingSource');
    Exit;
  end;
  if not Extracted then begin
    ProgressPage.SetText(CustomMessage('extracting'), CustomMessage('Working'));
    ProgressPage.ProgressBar.Style := npbstMarquee;
    ProgressPage.ProgressBar.Visible := True;
    ProgressPage.Show;
    try
      ExtractTemporaryFiles('{tmp}\payload\*');
      Extracted := True;
    finally
      ProgressPage.Hide;
    end;
  end;
  Report := ExpandConstant('{localappdata}\BoshyRandomizer\setup-prepare.json');
  WizardForm.PreparingLabel.Caption := CustomMessage('SourceDescription');
  if not Worker('prepare', ExpandConstant('{tmp}\payload'),
    '--source ' + Quote(Source) + ' --payload ' + Quote(ExpandConstant('{tmp}\payload')), Report) then
    Result := FailureMessage(Report);
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
    WizardForm.FinishedLabel.Caption := CustomMessage('Finished');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var Report: String;
begin
  if CurStep = ssPostInstall then begin
    Report := ExpandConstant('{localappdata}\BoshyRandomizer\setup-activate.json');
    if not Worker('activate', ExpandConstant('{tmp}\payload'),
      '--payload ' + Quote(ExpandConstant('{tmp}\payload')), Report) then
      RaiseException(FailureMessage(Report));
  end;
end;

function InitializeUninstall: Boolean;
var Form: TSetupForm; Hint: TNewStaticText; Choice: TNewCheckBox;
    Proceed, Cancel: TNewButton;
begin
  DeleteUserData := False;
  Result := True;
  if UninstallSilent then begin
    DeleteUserData := ExpandConstant('{param:DELETEUSERDATA|0}') = '1';
    Exit;
  end;
  Form := CreateCustomForm(ScaleX(540), ScaleY(235), False, True);
  try
    Form.Caption := CustomMessage('RemoveTitle');
    Form.ClientWidth := ScaleX(540);
    Form.ClientHeight := ScaleY(235);
    Form.Position := poScreenCenter;
    Hint := TNewStaticText.Create(Form);
    Hint.Parent := Form;
    Hint.AutoSize := False;
    Hint.SetBounds(ScaleX(24), ScaleY(24), ScaleX(492), ScaleY(95));
    Hint.WordWrap := True;
    Hint.Caption := CustomMessage('RemoveHint');
    Choice := TNewCheckBox.Create(Form);
    Choice.Parent := Form;
    Choice.SetBounds(ScaleX(24), ScaleY(125), ScaleX(492), ScaleY(36));
    Choice.Caption := CustomMessage('RemoveData');
    Choice.Checked := False;
    Proceed := TNewButton.Create(Form);
    Proceed.Parent := Form;
    Proceed.SetBounds(ScaleX(276), ScaleY(186), ScaleX(116), ScaleY(28));
    Proceed.Caption := CustomMessage('RemoveContinue');
    Proceed.ModalResult := mrOK;
    Cancel := TNewButton.Create(Form);
    Cancel.Parent := Form;
    Cancel.SetBounds(ScaleX(400), ScaleY(186), ScaleX(116), ScaleY(28));
    Cancel.Caption := SetupMessage(msgButtonCancel);
    Cancel.Cancel := True;
    Cancel.Default := True;
    Cancel.ModalResult := mrCancel;
    Form.ActiveControl := Cancel;
    Result := Form.ShowModal = mrOK;
    DeleteUserData := Result and Choice.Checked;
  finally
    Form.Free;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var Report, Extra: String;
begin
  if CurUninstallStep = usUninstall then begin
    Report := ExpandConstant('{tmp}\BoshyRandomizer-uninstall.json');
    Extra := '';
    if DeleteUserData then Extra := '--delete-user-data';
    if not Worker('uninstall', ExpandConstant('{app}\maintenance'), Extra, Report) then begin
      MsgBox(CustomMessage('RemoveError'), mbError, MB_OK);
      Abort;
    end;
    DeleteFile(ExpandConstant('{app}\.installation.lock'));
    RemoveDir(ExpandConstant('{app}\versions'));
  end;
end;
