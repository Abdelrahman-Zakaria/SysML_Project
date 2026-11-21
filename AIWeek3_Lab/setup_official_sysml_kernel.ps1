$ErrorActionPreference = "Stop"

$javaCommand = Get-Command java -ErrorAction SilentlyContinue
if (-not $javaCommand) {
    throw "Java 21 or newer is required. Install Java 21+ and run this script again."
}

$javaVersionOutput = (& java -version 2>&1 | Out-String)
if ($javaVersionOutput -match '(?:version\s+"?|openjdk\s+)(?<major>\d+)') {
    if ([int]$Matches.major -lt 21) {
        throw "Java 21 or newer is required. Detected Java $($Matches.major)."
    }
}

$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    throw "Activate the AIWeek3 virtual environment before running this script."
}
$pythonPath = $pythonCommand.Source

& $pythonPath -c "import jupyter_client"
if ($LASTEXITCODE -ne 0) {
    throw "Install the AIWeek3 requirements first, then rerun this script."
}

$release = Invoke-RestMethod `
    -Uri "https://api.github.com/repos/Systems-Modeling/SysML-v2-Pilot-Implementation/releases/latest" `
    -Headers @{ "User-Agent" = "AIWeek3-SysML-kernel-setup" }
$kernelAsset = $release.assets |
    Where-Object { $_.name -match '^sysml-jupyter-kernel-.*\.zip$' } |
    Select-Object -First 1
if (-not $kernelAsset) {
    throw "The latest official release did not include a sysml-jupyter-kernel ZIP asset."
}

$installId = [guid]::NewGuid().ToString("N")
$installDirectory = Join-Path ([System.IO.Path]::GetTempPath()) "AIWeek3-SysML-$installId"
$null = New-Item -ItemType Directory -Path $installDirectory
$archivePath = Join-Path $installDirectory $kernelAsset.name
$extractDirectory = Join-Path $installDirectory "kernel"

Invoke-WebRequest -Uri $kernelAsset.browser_download_url -OutFile $archivePath
Expand-Archive -LiteralPath $archivePath -DestinationPath $extractDirectory
$installer = Get-ChildItem -LiteralPath $extractDirectory -Filter "install.py" -Recurse |
    Select-Object -First 1
if (-not $installer) {
    throw "The official kernel archive did not contain install.py."
}

& $pythonPath $installer.FullName --sys-prefix
if ($LASTEXITCODE -ne 0) {
    throw "The official SysML kernel installer returned exit code $LASTEXITCODE."
}

Write-Host "Installed the OMG SysML v2 Pilot Implementation kernel from release $($release.tag_name)."
Write-Host "AIWeek3 will use the 'sysml' kernel to validate requirement proposals."
Write-Host "Installer files were kept in $installDirectory"
