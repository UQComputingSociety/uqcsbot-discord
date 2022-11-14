# UQCSbot

UQCSbot is our friendly chat bot used on the [UQCS Discord Server](https://discord.uqcs.org). For the UQCSbot used in our Slack team, see [UQCSbot-Slack](https://github.com/uqcomputing/uqcsbot-slack).

## Setup & Running Locally

UQCSbot uses [Poetry](https://python-poetry.org/) for dependency management. Once you have Poetry setup on your machine, you can setup and install dependencies by running:

```bash
poetry install
```

Access to the UQCSbot testing tokens and server is provided through the #bot-testing channel on our Discord.

### Using Docker (Recommended)

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

### Without Docker

You can also run the bot without Docker, however you currently require to have a PostgreSQL instance to connect to.

Export the environment variables into your environment, then run:
```
poetry shell
python -m uqcsbot
```

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
