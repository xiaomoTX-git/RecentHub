; RecentHub Windows 安装包脚本 (Inno Setup 6)
;
; 编译：
;   "C:\Users\<你>\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer\RecentHub.iss
;
; 前置：先由 PyInstaller 生成 dist\RecentHub\ (RecentHub.spec)
; 产物：dist\installer\RecentHub_Setup_v1.0.0.exe
;
; 安装策略：当前用户级安装 (PrivilegesRequired=lowest)，全程无 UAC 弹窗。
;   此时 {autopf} 解析为 %LOCALAPPDATA%\Programs，程序目录天然可写；
;   用户数据 (config.json / recenthub.db) 由程序自身写入
;   %APPDATA%\RecentHub 与 %LOCALAPPDATA%\RecentHub，卸载时保留。

#define AppName "RecentHub"
#define AppVersion "1.0.0"
#define AppExeName "RecentHub.exe"
#define SourceDir "..\dist\RecentHub"

[Setup]
AppId={{8E2C1F42-5B7A-4C9D-9E31-6F0A4B7D2C85}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Inno 默认会沿用"上次安装时勾选的任务"。此前版本的桌面快捷方式是未勾选，
; 升级安装时那个空选择会被继承，导致这里新设的"默认勾选"永远不生效。
; 关掉沿用，让每次安装都按本脚本的默认值呈现。
UsePreviousTasks=no
; 当前用户级安装：免管理员权限、免 UAC
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installer
OutputBaseFilename={#AppName}_Setup_v{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName}
; 安装前自动结束占用文件的旧实例 (只匹配本程序 exe 名，不影响其它进程)
CloseApplications=yes
RestartApplications=no
MinVersion=10.0

[Languages]
; Inno Setup 自带语言包不含简体中文，此处使用随本目录附带的社区版翻译文件
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; 桌面快捷方式默认勾选 (桌面软件惯例)
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; onedir 产物整体安装：RecentHub.exe + _internal\ (依赖与 resources)
Source: "{#SourceDir}\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[Code]
{ 结束正在运行的 RecentHub：安装与卸载时都先关闭旧实例，
  否则 onedir 目录下的 exe / dll 被占用会导致覆盖或删除失败。
  taskkill 只按本程序 exe 名匹配，不会波及其它进程 }

procedure KillRunningInstance();
var
  ResultCode: Integer;
begin
  Exec('taskkill.exe', '/F /IM {#AppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function InitializeSetup(): Boolean;
begin
  KillRunningInstance();
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    KillRunningInstance();
    { 清掉开机自启登记：否则卸载后 HKCU\...\Run 仍指向已删除的 exe，
      每次开机都会尝试拉起一个不存在的程序 }
    RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', '{#AppName}');
  end
  else if CurUninstallStep = usPostUninstall then
  begin
    { 用户数据默认保留（重装后配置与检索历史还在）；想彻底清干净由用户勾选。
      静默卸载不弹窗，一律保留，避免脚本化卸载误删数据 }
    if (not UninstallSilent)
       and (MsgBox('是否同时删除 RecentHub 的配置与本地检索数据库？' + #13#10 + #13#10 +
                   ExpandConstant('{userappdata}') + '\{#AppName}' + #13#10 +
                   ExpandConstant('{localappdata}') + '\{#AppName}' + #13#10 + #13#10 +
                   '选择「否」将保留，便于日后重装继续使用。',
                   mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES) then
    begin
      DelTree(ExpandConstant('{userappdata}\{#AppName}'), True, True, True);
      DelTree(ExpandConstant('{localappdata}\{#AppName}'), True, True, True);
    end;
  end;
end;