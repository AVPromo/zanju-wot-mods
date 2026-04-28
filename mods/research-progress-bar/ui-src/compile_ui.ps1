param(
    [string]$SourceFile = (Join-Path $PSScriptRoot 'src\ResearchProgressBarLobby.as'),
    [string]$OutputFile = (Join-Path $PSScriptRoot '..\res\gui\flash\research-progress-bar-lobby.swf'),
    [string]$StubSourceDir = (Join-Path $PSScriptRoot 'stubs-src'),
    [string]$StubSwc = (Join-Path $PSScriptRoot 'build\wot-stubs.swc'),
    [string]$TargetPlayer = '32.0',
    [string]$SwfVersion = '17'
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command mxmlc -ErrorAction SilentlyContinue)) {
    throw 'mxmlc was not found on PATH.'
}
if (-not (Get-Command compc -ErrorAction SilentlyContinue)) {
    throw 'compc was not found on PATH.'
}

$sourceDir = Split-Path -Path $SourceFile -Parent
$outputDir = Split-Path -Path $OutputFile -Parent
$stubDir = Split-Path -Path $StubSwc -Parent

New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
New-Item -ItemType Directory -Force -Path $stubDir | Out-Null

$stubArguments = @(
    '-output',
    $StubSwc,
    ('-source-path=' + $StubSourceDir),
    ('-include-sources=' + $StubSourceDir)
)

& compc @stubArguments

if ($LASTEXITCODE -ne 0) {
    throw "compc failed with exit code $LASTEXITCODE"
}

$arguments = @(
    '-output',
    $OutputFile,
    '-source-path',
    $sourceDir,
    ('-external-library-path+=' + $StubSwc),
    '-static-link-runtime-shared-libraries=true',
    ('-target-player=' + $TargetPlayer),
    ('-swf-version=' + $SwfVersion),
    '-default-size',
    '420',
    '180',
    '-default-frame-rate',
    '30',
    $SourceFile
)

& mxmlc @arguments

if ($LASTEXITCODE -ne 0) {
    throw "mxmlc failed with exit code $LASTEXITCODE"
}

Write-Host "Built UI SWF: $OutputFile"