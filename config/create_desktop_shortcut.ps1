$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('C:\Users\ravit\OneDrive\Desktop\Aura - Premium.lnk')
$Shortcut.TargetPath = 'D:\TiTech Prabha Solution\Aura AI\Aura AI\Aura-AI---Lite-main\Aura-AI---Lite-main\.venv\Scripts\pythonw.exe'
$Shortcut.Arguments = '"D:\TiTech Prabha Solution\Aura AI\Aura AI\Aura-AI---Lite-main\Aura-AI---Lite-main\main.py"'
$Shortcut.WorkingDirectory = 'D:\TiTech Prabha Solution\Aura AI\Aura AI\Aura-AI---Lite-main\Aura-AI---Lite-main'
$Shortcut.WindowStyle = 7
$Shortcut.Description = 'Launch Aura - Premium'
if ('D:\TiTech Prabha Solution\Aura AI\Aura AI\Aura-AI---Lite-main\Aura-AI---Lite-main\assets\Aura_Logo.ico') { $Shortcut.IconLocation = 'D:\TiTech Prabha Solution\Aura AI\Aura AI\Aura-AI---Lite-main\Aura-AI---Lite-main\assets\Aura_Logo.ico,0' }
$Shortcut.Save()