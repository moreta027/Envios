# Script para crear una tarea programada con el directorio de trabajo correcto para plGeneral.exe
# Ejecuta este script en PowerShell como administrador

$Action = New-ScheduledTaskAction -Execute "C:\Users\mmore\OneDrive\Documents\Envios\dist\plGeneral.exe" -WorkingDirectory "C:\Users\mmore\OneDrive\Documents\Envios"
$Trigger = New-ScheduledTaskTrigger -Daily -At 9am
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

# Redirige la salida estándar y de error a un archivo log
$Action.Arguments = "> C:\Users\mmore\OneDrive\Documents\Envios\plGeneral.log 2>&1"

Register-ScheduledTask -TaskName "plGeneral_Automatica" -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Force
Write-Host "Tarea programada creada con el directorio de trabajo correcto. El log estará en plGeneral.log"
