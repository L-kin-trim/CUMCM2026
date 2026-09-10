$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

function Invoke-Git {
    param([string[]]$GitArgs)
    & git @GitArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Git command failed: git $($GitArgs -join ' ')"
    }
}

try {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw 'Install Git for Windows first.'
    }
    Invoke-Git -GitArgs @('rev-parse', '--show-toplevel')
    $branch = & git symbolic-ref --quiet --short HEAD
    if ($LASTEXITCODE -ne 0 -or -not $branch) {
        throw 'Check out a branch before syncing.'
    }
    Invoke-Git -GitArgs @('remote', 'get-url', 'origin')
    Invoke-Git -GitArgs @('fetch', 'origin')
    & git show-ref --verify --quiet "refs/remotes/origin/$branch"
    $remoteStatus = $LASTEXITCODE
    if ($remoteStatus -eq 0) {
        & git merge-base --is-ancestor "origin/$branch" HEAD
        if ($LASTEXITCODE -ne 0) {
            throw "Remote changes found. Run: git pull --rebase --autostash origin $branch ; resolve any conflicts, then retry."
        }
    } elseif ($remoteStatus -ne 1) {
        throw 'Unable to inspect the remote branch.'
    }

    Invoke-Git -GitArgs @('add', '--all')
    & git diff --cached --quiet
    $diffStatus = $LASTEXITCODE
    if ($diffStatus -eq 1) {
        $message = 'Sync folder ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
        Invoke-Git -GitArgs @('commit', '-m', $message)
    } elseif ($diffStatus -ne 0) {
        throw 'Unable to inspect staged changes.'
    }
    Invoke-Git -GitArgs @('push', '--set-upstream', 'origin', $branch)
    Write-Host 'Sync successful.' -ForegroundColor Green
    exit 0
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
