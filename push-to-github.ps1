<#
.SYNOPSIS
  Pushes the Home Credit RiskIQ Enterprise Suite (home-credit-enterprise-suite)
  to your GitHub account, creating the repo if it doesn't exist yet.

.WHAT THIS DOES
  1. Checks git is installed.
  2. Asks for your GitHub username and a Personal Access Token (PAT) -- typed
     locally, never sent anywhere except to GitHub's own API/git over HTTPS.
     The token is NOT saved to disk and is NOT left in .git/config afterward.
  3. Configures git to use ALL your CPU cores for the compression step
     (this is the only part of a push that's actually CPU-bound -- the
     upload itself is bounded by your internet speed, not your laptop's
     resources; see the note printed at the end).
  4. Runs `git init` in the project folder if it isn't a repo yet, and
     stages everything NOT excluded by .gitignore (which already excludes
     your real raw data, real generated model outputs/reports, and
     project_config.json -- only code, notebooks with outputs cleared,
     docs, and governance files go to GitHub).
  5. Shows you EXACTLY what will be committed and asks you to confirm
     before anything is pushed -- nothing goes to GitHub silently.
  6. Creates the GitHub repo via the API if it doesn't exist yet (private
     by default -- pass -Public to make it public instead).
  7. Pushes to `main`.

.USAGE
  Open PowerShell (Run as Administrator is fine but not required -- this
  script doesn't install anything or touch system settings) and run:

      cd "C:\Users\rnand\Downloads\home-credit-enterprise-suite"
      powershell -ExecutionPolicy Bypass -File .\push-to-github.ps1

  To make the GitHub repo public instead of private:

      powershell -ExecutionPolicy Bypass -File .\push-to-github.ps1 -Public

.REQUIREMENTS
  - Git for Windows installed (https://git-scm.com/download/win, or
    `winget install --id Git.Git -e` from an elevated PowerShell).
  - A GitHub Personal Access Token with the "repo" and "workflow" scopes.
    Create one at https://github.com/settings/tokens -> "Generate new token
    (classic)" -> check "repo" and "workflow" -> Generate -> copy it (you
    only see it once).
#>

[CmdletBinding()]
param(
    [string]$ProjectPath = "C:\Users\rnand\Downloads\home-credit-enterprise-suite",
    [string]$RepoName    = "Home_Credit_RiskIQ_Enterprise_Suite",
    [switch]$Public
)

$ErrorActionPreference = "Stop"

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "    $msg" -ForegroundColor Yellow }
function Write-Err2($msg) { Write-Host "    $msg" -ForegroundColor Red }

# ---------------------------------------------------------------------------
Write-Step "Checking git is installed"
try {
    $gitVersion = git --version
    Write-Ok $gitVersion
} catch {
    Write-Err2 "git was not found. Install it first:"
    Write-Err2 "  winget install --id Git.Git -e   (run from an elevated PowerShell)"
    Write-Err2 "or download from https://git-scm.com/download/win"
    exit 1
}

# ---------------------------------------------------------------------------
Write-Step "Project folder"
if (-not (Test-Path $ProjectPath)) {
    Write-Err2 "Folder not found: $ProjectPath"
    Write-Err2 "Pass -ProjectPath <path> if your project lives somewhere else."
    exit 1
}
Set-Location $ProjectPath
Write-Ok "Working in: $ProjectPath"

if (-not (Test-Path ".gitignore")) {
    Write-Err2 "No .gitignore found here -- refusing to continue."
    Write-Err2 "(Without it, git add -A would try to stage your real raw data"
    Write-Err2 " and real generated model outputs, which should never go to"
    Write-Err2 " a public/shared GitHub repo.)"
    exit 1
}
Write-Ok ".gitignore present -- real data and generated outputs will be excluded."

# ---------------------------------------------------------------------------
Write-Step "GitHub credentials (typed locally, not saved to disk)"
$ghUser = Read-Host "GitHub username"
$ghTokenSecure = Read-Host "GitHub Personal Access Token (repo + workflow scopes)" -AsSecureString
$ghTokenBSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($ghTokenSecure)
$ghToken = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($ghTokenBSTR)
[System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ghTokenBSTR)

if ([string]::IsNullOrWhiteSpace($ghUser) -or [string]::IsNullOrWhiteSpace($ghToken)) {
    Write-Err2 "Username and token are both required."
    exit 1
}

$authHeader = @{ Authorization = "token $ghToken"; "User-Agent" = "home-credit-push-script" }

# ---------------------------------------------------------------------------
Write-Step "Speeding up the local git operations (compression uses all CPU cores)"
$cores = [Environment]::ProcessorCount
git config pack.threads 0            # 0 = auto-detect, use every core
git config core.compression 6        # balanced -- 9 is smaller but slower to compute
git config http.postBuffer 524288000 # 500MB buffer, avoids stalls on the bigger notebook files
Write-Ok "pack.threads=0 (uses all $cores logical cores you have), postBuffer=500MB"
Write-Warn2 "Note: this speeds up the LOCAL compression step. The actual upload to"
Write-Warn2 "GitHub is bounded by your internet upload speed, not your CPU/RAM --"
Write-Warn2 "there's no setting that makes the network faster. The repo content"
Write-Warn2 "here is small (code/docs/notebooks with outputs cleared, no real data),"
Write-Warn2 "so this should still be fast in practice."

# ---------------------------------------------------------------------------
Write-Step "Setting up the local git repo"
if (-not (Test-Path ".git")) {
    git init | Out-Null
    Write-Ok "git init done"
} else {
    Write-Ok "Already a git repo"
}

$gitUserName = git config user.name
$gitUserEmail = git config user.email
if ([string]::IsNullOrWhiteSpace($gitUserName)) {
    $gitUserName = Read-Host "git commit author name (e.g. your name)"
    git config user.name "$gitUserName"
}
if ([string]::IsNullOrWhiteSpace($gitUserEmail)) {
    $gitUserEmail = Read-Host "git commit author email"
    git config user.email "$gitUserEmail"
}

git branch -M main 2>$null | Out-Null

# ---------------------------------------------------------------------------
Write-Step "Staging files (this respects .gitignore -- real data/outputs are skipped)"
git add -A

$staged = git diff --cached --name-status
if ([string]::IsNullOrWhiteSpace($staged)) {
    Write-Warn2 "Nothing new to commit (working tree already matches the last commit, if any)."
} else {
    Write-Host ""
    Write-Host "----- Files that will be committed and pushed to GitHub -----" -ForegroundColor Magenta
    $staged | ForEach-Object { Write-Host "  $_" }
    Write-Host "---------------------------------------------------------------" -ForegroundColor Magenta
    $fileCount = ($staged -split "`n").Count
    Write-Host ""
    $confirm = Read-Host "Review the list above. Type YES to commit + push these $fileCount entries"
    if ($confirm -ne "YES") {
        Write-Warn2 "Aborted -- nothing was committed or pushed. Nothing changed on GitHub."
        git reset | Out-Null
        exit 0
    }

    Write-Step "Committing"
    $commitMsg = "Enterprise hardening pass: Mega Project 1 (Underwriting & Approval Intelligence) built and verified; suite corrected to its final 5-Mega-Project scope. See CHANGELOG.md for full disclosure of every fix."
    git commit -m "$commitMsg" | Out-Null
    Write-Ok "Committed."
}

# ---------------------------------------------------------------------------
Write-Step "Checking if the GitHub repo already exists"
$repoApiUrl = "https://api.github.com/repos/$ghUser/$RepoName"
$repoExists = $false
try {
    Invoke-RestMethod -Uri $repoApiUrl -Headers $authHeader -Method Get | Out-Null
    $repoExists = $true
    Write-Ok "Repo already exists: https://github.com/$ghUser/$RepoName"
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 404) {
        Write-Ok "Repo doesn't exist yet -- will create it."
    } else {
        Write-Err2 "Couldn't check repo existence: $($_.Exception.Message)"
        Write-Err2 "Check your token has the 'repo' scope and your username is correct."
        exit 1
    }
}

if (-not $repoExists) {
    Write-Step "Creating the GitHub repo"
    $visibilityText = if ($Public) { "public" } else { "private" }
    $body = @{
        name        = $RepoName
        description = "Home Credit Default Risk -- 5 Mega Project enterprise suite. Real trained models, real statistical analysis, deployable scoring services, enterprise governance/CI."
        private     = -not $Public
        auto_init   = $false
    } | ConvertTo-Json

    try {
        $created = Invoke-RestMethod -Uri "https://api.github.com/user/repos" -Headers $authHeader -Method Post -Body $body -ContentType "application/json"
        Write-Ok "Created $visibilityText repo: $($created.html_url)"
    } catch {
        Write-Err2 "Failed to create repo: $($_.Exception.Message)"
        exit 1
    }
}

# ---------------------------------------------------------------------------
Write-Step "Pushing to GitHub"

# Remote is set to the plain (token-free) URL for normal future use...
$plainRemote = "https://github.com/$ghUser/$RepoName.git"
$existingRemote = git remote get-url origin 2>$null
if ($existingRemote) {
    git remote set-url origin $plainRemote
} else {
    git remote add origin $plainRemote
}

# ...but THIS push uses a one-time authenticated URL so the token is never
# written into .git/config on disk.
$authedRemote = "https://$($ghUser):$($ghToken)@github.com/$ghUser/$RepoName.git"

try {
    git push $authedRemote main
    Write-Ok "Pushed to https://github.com/$ghUser/$RepoName"
} catch {
    Write-Err2 "Push failed: $($_.Exception.Message)"
    Write-Err2 "If this is 'main' vs an existing default branch, try:"
    Write-Err2 "  git push $plainRemote main --force-with-lease   (only if you're SURE the remote is empty/yours)"
    exit 1
}

# Clear the token from this process's memory as soon as we're done with it.
$ghToken = $null
[System.GC]::Collect()

Write-Host ""
Write-Host "Done. Repo: https://github.com/$ghUser/$RepoName" -ForegroundColor Green
Write-Host "Your git remote 'origin' is set to the plain HTTPS URL (no token stored)." -ForegroundColor Green
Write-Host "Next push, Windows will prompt you to sign in via the Git Credential Manager." -ForegroundColor Green
