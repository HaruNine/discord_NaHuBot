import asyncio
from utils.logger import setup_loggers
from bot_init import bot, token
from commands.commands import (
    UtilsCommands, MusicCommands
    )

@bot.event
async def on_command_error(ctx, error):
    print(f"명령어 에러: {error}")
    await ctx.send(f"에러 발생: {error}", delete_after=10)

async def main():
    setup_loggers()
    async with bot:
        await bot.add_cog(MusicCommands(bot))
        await bot.add_cog(UtilsCommands(bot))
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main()) 