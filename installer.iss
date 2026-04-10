; Inno Setup Script for Product Photo Manager
; Download Inno Setup: https://jrsoftware.org/isinfo.php
; Compile: Right-click this file → Compile with Inno Setup

[Setup]
AppName=Product Photo Manager
AppVersion=1.0.0
AppPublisher=ParkBakery
AppPublisherURL=https://github.com/ParkBakery
DefaultDirName={autopf}\ProductPhotoManager
DefaultGroupName=Product Photo Manager
OutputDir=dist
OutputBaseFilename=ProductPhotoManager-Setup
Compression=lzma2/ultra64
SolidCompression=yes
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\ProductPhotoManager.exe
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "startmenuicon"; Description: "Create a &Start Menu shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "dist\ProductPhotoManager\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Product Photo Manager"; Filename: "{app}\ProductPhotoManager.exe"; IconFilename: "{app}\app_icon.ico"
Name: "{group}\Uninstall Product Photo Manager"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Product Photo Manager"; Filename: "{app}\ProductPhotoManager.exe"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\ProductPhotoManager.exe"; Description: "Launch Product Photo Manager"; Flags: nowait postinstall skipifsilent
