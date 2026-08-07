Option Explicit

Dim shell, fso, appDir, appPath, command
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

appDir = fso.GetParentFolderName(WScript.ScriptFullName)
appPath = fso.BuildPath(appDir, "desktop_app.py")

If fso.FileExists("C:\Python314\pythonw.exe") Then
  command = Quote("C:\Python314\pythonw.exe") & " " & Quote(appPath)
ElseIf fso.FileExists(shell.ExpandEnvironmentStrings("%USERPROFILE%") & "\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe") Then
  command = Quote(shell.ExpandEnvironmentStrings("%USERPROFILE%") & "\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe") & " " & Quote(appPath)
ElseIf fso.FileExists("C:\Python314\python.exe") Then
  command = Quote("C:\Python314\python.exe") & " " & Quote(appPath)
ElseIf fso.FileExists(shell.ExpandEnvironmentStrings("%USERPROFILE%") & "\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe") Then
  command = Quote(shell.ExpandEnvironmentStrings("%USERPROFILE%") & "\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe") & " " & Quote(appPath)
Else
  MsgBox "Python nao encontrado. Instale o Python 3 para abrir o sistema.", vbExclamation, "Ponto Funcionarios"
  WScript.Quit 1
End If

shell.CurrentDirectory = appDir
shell.Run command, 0, False

Function Quote(value)
  Quote = """" & value & """"
End Function
