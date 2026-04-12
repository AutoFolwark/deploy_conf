param(
    [string]$command = "up",
    [string]$env = "dev",
    # Default: merge general base + dev overlay. Pass a single path to override (e.g. demo/docker-compose.demo.yml).
    [string]$compose_file = ""
)

# Align with Makefile: default compose file per environment when none is passed.
if ([string]::IsNullOrEmpty($compose_file) -and $env -eq "demo") {
    $compose_file = "demo/docker-compose.demo.yml"
}
if ([string]::IsNullOrEmpty($compose_file) -and $env -eq "prod") {
    $compose_file = "prod/docker-compose.yml"
}

function Get-ComposeArgs {
    param([string]$ComposeFile)
    if ($ComposeFile) {
        return ,(@("-f", $ComposeFile))
    }
    return ,(@("--profile", "embedded-datastores", "-f", "general/docker-compose.base.yml", "-f", "dev/docker-compose.dev.yml"))
}

$composeArgs = Get-ComposeArgs -ComposeFile $compose_file

function Test-UsePreflight {
    param([string]$ComposeFile)
    if ([string]::IsNullOrEmpty($ComposeFile)) {
        return $true
    }
    $norm = $ComposeFile -replace '\\', '/'
    return $norm -match '(?i)demo/docker-compose\.demo\.yml$'
}

function Invoke-StackUp {
    param([string]$EnvName, [string]$ComposeFile, [string[]]$ComposeArgsFull)

    docker compose @ComposeArgsFull pull

    if ($EnvName -eq "prod") {
        infisical run --env=$EnvName -- docker compose @ComposeArgsFull up -d
        return
    }

    if (Test-UsePreflight -ComposeFile $ComposeFile) {
        $bash = Get-Command bash -ErrorAction SilentlyContinue
        if (-not $bash) {
            Write-Error "bash is not in PATH. scripts/pg_stack_up.sh requires bash (e.g. Git for Windows). On Linux/macOS use: make up"
            exit 1
        }
        $mode = if ($ComposeFile -and (($ComposeFile -replace '\\', '/') -match '(?i)demo/docker-compose\.demo\.yml$')) {
            "demo"
        } else {
            "dev"
        }
        infisical run --env=$EnvName -- bash ./scripts/pg_stack_up.sh $mode
    } else {
        infisical run --env=$EnvName -- docker compose @ComposeArgsFull up -d
    }
}

switch ($command.ToLower()) {
    "up" {
        Invoke-StackUp -EnvName $env -ComposeFile $compose_file -ComposeArgsFull $composeArgs
    }
    "down" {
        docker compose @composeArgs down
    }
    "logs" {
        docker compose @composeArgs logs -f
    }
    "restart" {
        docker compose @composeArgs down
        Invoke-StackUp -EnvName $env -ComposeFile $compose_file -ComposeArgsFull $composeArgs
    }
    "clean-volumes" {
        docker compose @composeArgs down -v
    }
    "help" {
        Write-Host "Available commands:" -ForegroundColor Green
        Write-Host "  up            - Pull images and start containers (dev/demo: runs scripts/pg_stack_up.sh preflight)" -ForegroundColor White
        Write-Host "  down/logs     - If compose vars are not in your environment, run:" -ForegroundColor White
        Write-Host "                infisical run --env=<dev|demo|prod> -- .\run.ps1 <command>" -ForegroundColor White
        Write-Host "  down          - Stop and remove containers" -ForegroundColor White
        Write-Host "  logs          - Follow container logs" -ForegroundColor White
        Write-Host "  restart       - Stop and start containers" -ForegroundColor White
        Write-Host "  clean-volumes - Stop containers and remove volumes" -ForegroundColor White
        Write-Host "  help          - Show this help message" -ForegroundColor White
        Write-Host ""
        Write-Host "Parameters:" -ForegroundColor Green
        Write-Host "  -command      - Command to execute (default: up)" -ForegroundColor White
        Write-Host "  -env          - Environment for Infisical (default: dev); demo selects demo/docker-compose.demo.yml" -ForegroundColor White
        Write-Host "  -compose_file - Single compose file path, or omit for dev (base + dev overlay)" -ForegroundColor White
        Write-Host ""
        Write-Host "Examples:" -ForegroundColor Green
        Write-Host "  .\run.ps1 up" -ForegroundColor Yellow
        Write-Host "  .\run.ps1 -command up -env demo" -ForegroundColor Yellow
        Write-Host "  .\run.ps1 -command logs" -ForegroundColor Yellow
        Write-Host "  .\run.ps1 -command up -env prod -compose_file prod/docker-compose.yml" -ForegroundColor Yellow
    }
    default {
        Write-Host "Unknown command: $command" -ForegroundColor Red
        Write-Host "Available commands: up, down, logs, restart, clean-volumes, help" -ForegroundColor White
        Write-Host "Use 'help' command for more information." -ForegroundColor White
    }
}
