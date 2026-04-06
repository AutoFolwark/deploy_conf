param(
    [string]$command = "up",
    [string]$env = "dev",
    # Default: merge general base + dev overlay. Pass a single path to override (e.g. demo/docker-compose.demo.yml).
    [string]$compose_file = ""
)

$envFileArgs = @()
if (Test-Path -Path ".env") {
    $envFileArgs = @("--env-file", ".env")
}
$composeArgs = if ($compose_file) {
    $envFileArgs + @("-f", $compose_file)
} else {
    $envFileArgs + @("-f", "general/docker-compose.base.yml", "-f", "dev/docker-compose.dev.yml")
}

switch ($command.ToLower()) {
    "up" {
        docker compose @composeArgs pull
        infisical run --env=$env -- docker compose @composeArgs up -d
    }
    "down" {
        docker compose @composeArgs down
    }
    "logs" {
        docker compose @composeArgs logs -f
    }
    "restart" {
        docker compose @composeArgs down
        infisical run --env=$env -- docker compose @composeArgs up -d
    }
    "clean-volumes" {
        docker compose @composeArgs down -v
    }
    "help" {
        Write-Host "Available commands:" -ForegroundColor Green
        Write-Host "  up            - Pull images and start containers" -ForegroundColor White
        Write-Host "  down          - Stop and remove containers" -ForegroundColor White
        Write-Host "  logs          - Follow container logs" -ForegroundColor White
        Write-Host "  restart       - Stop and start containers" -ForegroundColor White
        Write-Host "  clean-volumes - Stop containers and remove volumes" -ForegroundColor White
        Write-Host "  help          - Show this help message" -ForegroundColor White
        Write-Host ""
        Write-Host "Parameters:" -ForegroundColor Green
        Write-Host "  -command      - Command to execute (default: up)" -ForegroundColor White
        Write-Host "  -env          - Environment for Infisical (default: dev)" -ForegroundColor White
        Write-Host "  -compose_file - Single compose file path, or omit for dev (base + dev overlay)" -ForegroundColor White
        Write-Host ""
        Write-Host "Examples:" -ForegroundColor Green
        Write-Host "  .\run.ps1 up" -ForegroundColor Yellow
        Write-Host "  .\run.ps1 -command logs" -ForegroundColor Yellow
        Write-Host "  .\run.ps1 -command up -env prod -compose_file prod/docker-compose.yml" -ForegroundColor Yellow
    }
    default {
        Write-Host "Unknown command: $command" -ForegroundColor Red
        Write-Host "Available commands: up, down, logs, restart, clean-volumes, help" -ForegroundColor White
        Write-Host "Use 'help' command for more information." -ForegroundColor White
    }
}