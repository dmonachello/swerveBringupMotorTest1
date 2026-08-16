@echo off
setlocal
call tools\can_nt\run_can_nt.cmd --cli --no-can %*
endlocal
