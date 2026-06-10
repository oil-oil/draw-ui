param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $ArgsList
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir "generate_image.py"
$python = if ($env:DRAW_PYTHON) { $env:DRAW_PYTHON } else { "python" }

$framePath = ""
$remaining = [System.Collections.Generic.List[string]]::new()

for ($i = 0; $i -lt $ArgsList.Count; $i++) {
    if ($ArgsList[$i] -eq "--frame") {
        if ($i + 1 -ge $ArgsList.Count) {
            throw "--frame requires a path"
        }
        $framePath = $ArgsList[$i + 1]
        $i++
        continue
    }
    $remaining.Add($ArgsList[$i])
}

$commandArgs = @($pythonScript)
if ($framePath) {
    $commandArgs += @("--ref", $framePath)
}
$commandArgs += $remaining.ToArray()

& $python @commandArgs
exit $LASTEXITCODE
