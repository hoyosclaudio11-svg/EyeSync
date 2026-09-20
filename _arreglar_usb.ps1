# Arreglo anti-caidas USB para la webcam de EyeSync (requiere admin).
# Escribe el resultado en datos\_usb_fix.log
$log = "C:\Users\chito\OneDrive - Plan Sarmiento\Escritorio\EyeSync\datos\_usb_fix.log"
"=== EyeSync fix USB - $(Get-Date) ===" | Out-File $log -Encoding utf8

# 1) USB selective suspend OFF (enchufado y bateria)
powercfg /setacvalueindex SCHEME_CURRENT 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226 0 2>&1 | Out-Null
powercfg /setdcvalueindex SCHEME_CURRENT 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226 0 2>&1 | Out-Null
powercfg /setactive SCHEME_CURRENT 2>&1 | Out-Null
$sus = powercfg /q SCHEME_CURRENT 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226 |
    Select-String "0x" | Select-Object -Last 2
"1) Selective suspend AC/DC: $($sus.Line -join ' | ')" | Out-File $log -Append -Encoding utf8

# 2) "Permitir que el equipo apague este dispositivo" = NO, para la webcam
try {
    Get-CimInstance -Namespace root/wmi -ClassName MSPower_DeviceEnable |
        Where-Object { $_.InstanceName -like "*1B3F*" } |
        ForEach-Object {
            $_.Enable = $false
            Set-CimInstance -InputObject $_
            "2) DeviceEnable=NO para $($_.InstanceName)" | Out-File $log -Append -Encoding utf8
        }
} catch { "2) ERROR WMI: $_" | Out-File $log -Append -Encoding utf8 }

# 3) Gestion de energia mejorada OFF en los Device Parameters de la camara
try {
    Get-ChildItem "HKLM:\SYSTEM\CurrentControlSet\Enum\USB\VID_1B3F&PID_2247" -ErrorAction SilentlyContinue |
        ForEach-Object {
            $dp = Join-Path $_.PSPath "Device Parameters"
            if (Test-Path $dp) {
                Set-ItemProperty -Path $dp -Name "EnhancedPowerManagementEnabled" -Value 0 -Type DWord
                "3) EnhancedPowerManagementEnabled=0 en $($_.PSChildName)" | Out-File $log -Append -Encoding utf8
            }
        }
} catch { "3) ERROR registro: $_" | Out-File $log -Append -Encoding utf8 }

"=== FIN ===" | Out-File $log -Append -Encoding utf8
