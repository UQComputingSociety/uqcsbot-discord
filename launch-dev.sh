#!/bin/bash

# Oh hey! This is a small script to get the bot up and running for Unix-like systems.
# There are comments throughout if you're curious on how this works.

if [ "$1" == "--help" ]
then
    echo "UQCSbot launcher script"
    echo "Usage: ./launch-dev.sh [.env file]"
    echo
    echo "The script will automatically attempt to read the .env file unless overridden."
    echo "If no .env file can be found, it will ask the user for their testing token."
    exit 0
fi

# If the script is run with a custom .env file, use that.
if [ ! -z "$1" ]
then
    # Make sure that the file exists.
    if [ ! -f $1 ]
    then
        echo The file $1 does not exist.
        exit 1 
    fi

    echo "Running with file $1"
    export $(grep "^[^#]" $1 | xargs)
else
    # Otherwise, check if a .env file exists and use that.
    if [ -f ".env" ]
    then
        echo "Running with found .env file"
        export $(grep "^[^#]" .env | xargs)
    else
        # Otherwise, ask the user for their bot token directly.
        echo -n "Please enter your Discord bot token:"
        read bot_token
        export DISCORD_BOT_TOKEN $botToken
    fi
fi

# Launch the bot
echo "Launching bot with Poetry"
echo "-------------------------"
poetry run python -m uqcsbot
