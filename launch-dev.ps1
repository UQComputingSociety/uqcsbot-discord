
# Oh hey! This is a small script to get the bot up and running for Windows systems.
# You might need to adjust the execution policy for PowerShell if you haven't already for this script to run.
# There are comments throughout if you're curious on how this works.

# Reads, parses, and imports the env file as session environment variables.
function exportEnvFile {
    param ([string] $File)

    foreach ($line in Get-Content $File) {
        if ($line.StartsWith("#")) { continue }
        $splitLine = $line.Split("=", 2)
        [Environment]::SetEnvironmentVariable($splitline[0], $splitline[1])
    }
}

$firstArg = $args[0]

if ($firstArg -eq "--help") {
    Write-Host "UQCSbot launcher script"
    Write-Host "Usage: ./launch-dev.sh [.env file]"
    Write-Host
    Write-Host "The script will automatically attempt to read the .env file unless overridden."
    Write-Host "If no .env file can be found, it will ask the user for their testing token."
    Exit
}

# Checks if a specific .env file has been passed as an argument.
if ($firstArg) {
    if (Test-Path $firstArg) {
        Write-Host "Running with file $firstArg"
        exportEnvFile $firstArg
    } else {
        Write-Host "The file $firstArg does not exist."
        Exit 1
    }
} else {

    if (Test-Path ".env") {
        Write-Host "Running with found .env file"
        exportEnvFile ".env"
    }
    else {
        $token = Read-Host -Prompt "Please enter your Discord bot token"
        [Environment]::SetEnvironmentVariable("DISCORD_BOT_TOKEN", $token)
    }
}

# Launch the bot
Write-Host "Launching bot with Poetry"
Write-Host "-------------------------"
poetry run python -m uqcsbot
