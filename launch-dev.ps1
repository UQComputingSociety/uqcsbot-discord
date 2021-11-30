
# Oh hey! This is a small script to get the bot up and running for Windows systems.
# You might need to adjust the execution policy for PowerShell if you haven't already for this script to run.
# There are comments throughout if you're curious on how this works.

if ($args[0] -eq "--help") {
    Write-Host "UQCSbot launcher script"
    Write-Host "Usage: ./launch-dev.sh [.env file]"
    Write-Host
    Write-Host "The script will automatically attempt to read the .env file unless overridden."
    Write-Host "If no .env file can be found, it will ask the user for their testing token."
}