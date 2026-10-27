' Stable, cwd-independent owner entry point. No shell or environment setup.
Option Explicit
Dim files, folder, executable, shell
Set files = CreateObject("Scripting.FileSystemObject")
folder = files.GetParentFolderName(WScript.ScriptFullName)
executable = files.BuildPath(folder, "src-tauri\target\release\resonance-workbench.exe")
If Not files.FileExists(executable) Or Not files.FileExists(files.BuildPath(folder, "src-tauri\target\release\bridge.py")) Or Not files.FileExists(files.BuildPath(folder, "src-tauri\target\release\python\python.exe")) Then
  MsgBox "The Workbench application bundle is incomplete. Build it once with npm run bundle in the workbench folder.", vbExclamation, "Resonance Workbench"
  WScript.Quit 1
End If
Set shell = CreateObject("WScript.Shell")
shell.Run Chr(34) & executable & Chr(34), 1, False
