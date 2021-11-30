# UQCSbot

UQCSbot is our friendly chat bot used on the [UQCS Discord Server](https://discord.uqcs.org). For the UQCSbot used in our Slack team, see [UQCSbot-Slack](https://github.com/uqcomputing/uqcsbot).

Our bot is open to feedback and improvements by our community and we encourage you to get involved. If you're looking to get started and learn how to participate in open source, this is a great first step.

## Setup & Running Locally

Make sure you have installed:
- [Python](https://python.org) (Ideally 3.9 or newer)
- [Poetry](https://python-poetry.org/) 

UQCSbot uses [Poetry](https://python-poetry.org/) for dependency management. Once you have Poetry setup on your machine, you can setup and install the required dependencies by running:

```bash
poetry install
```

There are two options to running the bot locally:
- For most people, following the simple setup will allow you to work with the bot using an in-memory database for testing.
- If you are familiar with Docker, and/or needing a proper PostgreSQL database, use the Docker setup instructions. 

### Getting a testing bot token

To get access to the testing server and receive a testing token, run the `command` in the #bot-testing channel in the Discord. The bot will DM you a testing token which will give you access to one of the four bots in the testing server.

An invite to the bot testing server can be found in the pinned messages of the #bot-testing channel.

Alternatively, you can create your own bot and add it to your own server by following _these instructions_.

### Simple Setup

The simplest way to get up and running is to run either `launch-dev.ps1` on Windows (using PowerShell) or `launch-dev.sh` on Unix based systems (notably macOS & Linux).

The script will import a `.env` file in the root directory, and will also accept a file path to an alternative .env file. If no `.env` file is detected, the script will ask you for your bot token. You can use `.env.example` as a basis for your own .env file.

Alternatively, you can export the required environment variables and run the following:
```
poetry run python -m uqcsbot
```

### Setup with Docker

If you're going to use Docker as your dev environment, make sure you have:
* [Docker](https://docs.docker.com/engine/install/)
* [Docker Compose](https://docs.docker.com/compose/install/)

Ensure that you have the `.env` file with your allocated bot token and the default PostgeSQL connection string.

To build and start Docker, you can run: (Note that depending on how Docker is configured, you may need to prepend `sudo`)
```
docker-compose up -d --build
```

To shut down the Docker environment, run:
```
docker-compose down
```

Make sure you shut down your Docker environment after you're finished as you may accidentally keep the bot running in the background.

### Environment Variables

See the [Wiki page](https://github.com/UQComputingSociety/uqcsbot-discord/wiki/Tokens-and-Environment-Variables) and the [.env.example](.env.example) for specifics about what environment variables the bot needs and uses.


## Development Resources

If this is your first time working on an open source project, we're here to walk you through every step of the way.

* If you're completely new to Git, check out [Atlassian's Git Tutorial site](https://www.atlassian.com/git).

* If you're unsure what to work on, check out the [issues labelled good first issue](https://github.com/UQComputingSociety/uqcsbot-discord/labels/good%20first%20issue).

* UQCSbot uses the open source [Discord.py project](https://github.com/Rapptz/discord.py), check out the docs at: <https://discordpy.readthedocs.io/>

* If you want more information around working with Discord itself, check out the [Discord Developer Documentation](https://discord.com/developers/docs).

If you have any questions, reach out in the #bot-testing channel in the Discord!

## License

UQCSbot is licensed under the [MIT License](LICENSE).
