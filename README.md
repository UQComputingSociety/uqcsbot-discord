# UQCSbot

UQCSbot is our friendly chat bot used on the [UQCS Discord Server](https://discord.uqcs.org). For the UQCSbot used in our Slack team, see [UQCSbot-Slack](https://github.com/uqcomputing/uqcsbot).

Our bot is open to feedback and improvements by our community and we encourage you to get involved. If you're looking to get started and learn how to participate in open source, this is a great first step.

## Setup & Running Locally

UQCSbot uses [Poetry](https://python-poetry.org/) for dependency management. Once you have Poetry setup on your machine, you can setup and install the required dependencies by running:

```bash
poetry install
```

There are two options to running the bot locally:
- For most people, following the simple setup will allow you to work with the bot using an in-memory database for testing.
- If you are familiar with Docker, or wanting to develop within a production like environment, use the Docker setup instructions. 

### Getting a testing bot token

To get access to the testing server and receive a testing token, run the _command_ in the #bot-testing channel in the Discord. The bot will DM you a testing token which will give you access to one of the four bots in the testing server.

An invite to the bot testing server can be found in the pinned messages of the #bot-testing channel.

Alternatively, you can create your own bot and add it to a server by following _these instructions_.

### Simple Setup

You can also run the bot without Docker, however you currently require to have a PostgreSQL instance to connect to.

Export the environment variables into your environment, then run:
```
poetry shell
python -m uqcsbot
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

* `DISCORD_BOT_TOKEN` for the Discord provided bot token.
* `POSTGRES_URI_BOT` for the PostgreSQL connection string. 

The `.env.example` file contains a basis for what you can use as a .env file. (Used for Docker only)

## Testing

Coming soon.

## Development Resources

If this is your first time working on an open source project, we're here to walk you through every step of the way.

If you're completely new to Git, check out [Atlassian's Git Tutorial site](https://www.atlassian.com/git).

<!-- If you're feeling ready to start working on the repository, check out this tutorial on forking and creating a pull request: ** TODO **  -->

If you're unsure what to work on, check out the [issues labelled good first issue](https://github.com/UQComputingSociety/uqcsbot-discord/labels/good%20first%20issue).

UQCSbot uses the open source [Discord.py project](https://github.com/Rapptz/discord.py), check out the docs at: <https://discordpy.readthedocs.io/>

If you want more information around working with Discord itself, check out the [Discord Developer Documentation](https://discord.com/developers/docs).

If you have any questions, reach out in the #bot-testing channel in the Discord!

## License

UQCSbot is licensed under the [MIT License](LICENSE).
