@echo off 

set BatFile=%1
set /a T=%2
set /a F= 0

for /F %%A in ('powershell -Command "(Start-Process -PassThru -FilePath cmd.exe -ArgumentList \"%BatFile%\" -WindowStyle Hidden).Id"') do (set PID=%%A)



:check
tasklist /FI "PID eq %PID%" 2>nul | find /i /n "%PID%" > nul

IF "%ERRORLEVEL%" EQU "0" (
	goto check_T
) ELSE (
	echo "[+] Task Fininshed"
	echo :Finished > status.lck
	goto exit
)

:check_T
IF %F% LEQ %T% (
	goto wait
) ELSE (
	echo "[-] Task timeout"
	echo :Timeout > status.lck
	goto kill
)

:wait
powershell Start-Sleep 10
set /a F+=10
goto check

:kill
taskkill /PID "%PID%" /T /F >nul
goto exit

:exit