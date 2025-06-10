import os
import logging
from dotenv import load_dotenv
import discord
from discord.ext import commands
import aiohttp
from fuzzywuzzy import process
import asyncio

# 로깅 설정 (logger.py에서 분리 가능)
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.WARNING)

ytdl_logger = logging.getLogger('yt_dlp')
ytdl_logger.setLevel(logging.ERROR)

logging.getLogger('discord.player').setLevel(logging.ERROR)

BOT_MODE = os.getenv('BOT_MODE', 'production')

if BOT_MODE == 'development':
    discord_logger.setLevel(logging.DEBUG)
    ytdl_logger.setLevel(logging.INFO)
else:
    discord_logger.setLevel(logging.WARNING)
    ytdl_logger.setLevel(logging.ERROR)

# 절대경로로 .env 지정
dotenv_path = '/app/.env'
load_dotenv(dotenv_path=dotenv_path)
token = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

class FuzzyBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.remove_command('help')
        self.session = None
        self.command_queue = asyncio.Queue()
        self.processing_command = False

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        self.loop.create_task(self.process_commands())

    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

    def get_commands(self):
        return list(self.all_commands.values())

    async def get_context(self, message, *, cls=commands.Context):
        ctx = await super().get_context(message, cls=cls)
        if ctx.command is None:
            command_name = ctx.invoked_with
            commands = self.get_commands()
            matches = process.extractBests(command_name, [cmd.name for cmd in commands], score_cutoff=80, limit=1)
            if matches:
                ctx.command = self.all_commands.get(matches[0][0])
            else:
                similar_commands = process.extractBests(command_name, [cmd.name for cmd in commands], score_cutoff=60)
                if similar_commands:
                    suggestions = ', '.join([match[0] for match in similar_commands])
                    await message.channel.send(f"어머나, '{command_name}' 명령어를 찾을 수 없어요: 비슷한 명령어: {suggestions}")
        return ctx

    async def on_ready(self):
        print(f'바다가 준비 완료했어요! {self.user}로 로그인했답니다~')

    async def process_commands(self):
        while True:
            ctx = await self.command_queue.get()
            try:
                await self.invoke(ctx)
            except Exception as e:
                await ctx.send(f"명령어 처리 중 오류가 발생했어요: {str(e)}")
            finally:
                self.command_queue.task_done()

    async def on_message(self, message):
        if message.author.bot:
            return
        ctx = await self.get_context(message)
        await self.command_queue.put(ctx)

    async def on_ready(self):
        print(f'바다가 준비 완료했어요! {self.user}로 로그인했답니다~')

bot = FuzzyBot(command_prefix='??', intents=intents)

@bot.check
async def globally_block_single_exclamation(ctx):
    return not ctx.prefix == '!' 

@bot.event
async def on_ready():
    await bot.change_presence(
        status=discord.Status.online,  # online, idle, dnd, invisible
        activity=discord.Game("재획하면서 노래 찾는중.. 🐳")
    )