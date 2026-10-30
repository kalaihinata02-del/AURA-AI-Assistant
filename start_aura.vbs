Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
venvPythonW = root & "\.venv\Scripts\pythonw.exe"
mainPy = root & "\main.py"

If fso.FileExists(venvPythonW) Then
  shell.Run Chr(34) & venvPythonW & Chr(34) & " " & Chr(34) & mainPy & Chr(34), 0, False
ElseIf fso.FileExists(root & "\pythonw.exe") Then
  shell.Run Chr(34) & root & "\pythonw.exe" & Chr(34) & " " & Chr(34) & mainPy & Chr(34), 0, False
Else
  shell.Run "pythonw.exe " & Chr(34) & mainPy & Chr(34), 0, False
End If
