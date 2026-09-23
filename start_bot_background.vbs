Set WshShell = CreateObject("WScript.Shell")
' Run start_bot.bat completely hidden in background (0 = hide window)
WshShell.Run "cmd /c """ & WshShell.CurrentDirectory & "\start_bot.bat""", 0, False
Set WshShell = Nothing
