import discord
from discord.ext import commands
from quiz_bot import config, QuizCommands

def main():
    # Initialize bot with intents
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="/", intents=intents)

    @bot.event
    async def on_ready():
        print(f"✅ Bot siap login sebagai {bot.user}")
        try:
            # Create a single command group instance
            quiz_commands = QuizCommands(bot)
            # Add the entire group to the command tree
            bot.tree.add_command(quiz_commands)
            # Sync the command tree
            synced = await bot.tree.sync()
            print(f"✅ Sinkronisasi {len(synced)} slash command")
        except Exception as e:
            print(f"❌ Error sync command: {e}")

    # Run the bot
    bot.run(config.DISCORD_TOKEN)

if __name__ == "__main__":
    main()