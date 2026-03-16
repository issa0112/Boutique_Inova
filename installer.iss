; --- Inno Setup Script pour Boutique Inova ---

[Setup]
AppName=Boutique Inova
AppVersion=1.0
DefaultDirName={pf}\Boutique
DefaultGroupName=Boutique
OutputDir=.
OutputBaseFilename=setup_boutique
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin

[Files]
; Copie tous les fichiers générés par PyInstaller dans dist\desktop
Source: "dist\desktop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Raccourci menu démarrer
Name: "{group}\Boutique Inova"; Filename: "{app}\desktop.exe"; WorkingDir: "{app}"
; Raccourci bureau
Name: "{commondesktop}\Boutique Inova"; Filename: "{app}\desktop.exe"; WorkingDir: "{app}"

[Run]
; Lancer l'application après installation
Filename: "{app}\desktop.exe"; Description: "Lancer Boutique Inova"; Flags: nowait postinstall skipifsilent