; Installer recipe for T23. Compile with Inno Setup 6 after build.py.
[Setup]
AppId=ebook2mp4
AppName=ebook2mp4 書籍製作工具
AppVersion=0.1.0
DefaultDirName={localappdata}\Programs\ebook2mp4
DefaultGroupName=ebook2mp4
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=ebook2mp4-T01-setup
Compression=lzma2
SolidCompression=yes
UninstallDisplayIcon={app}\ebook2mp4.exe
WizardStyle=modern

[Files]
Source: "..\dist\ebook2mp4\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\ebook2mp4"; Filename: "{app}\ebook2mp4.exe"
Name: "{autodesktop}\ebook2mp4"; Filename: "{app}\ebook2mp4.exe"

[Run]
Filename: "{app}\ebook2mp4.exe"; Description: "啟動書籍製作工具"; Flags: nowait postinstall skipifsilent
