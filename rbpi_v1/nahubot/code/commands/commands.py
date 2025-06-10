from discord.ext import commands
from handlers.handlers_music import (
    handle_now_playing, handle_play_first, handle_stop, handle_leave, handle_volume, handle_play, handle_search, handle_playlist_play, handle_queue
)
from handlers.handlers_utile import (
    handle_help
)
from uiux.music_player import MusicPlayer

class MusicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.players = {}

    def get_player(self, ctx):
        if ctx.guild.id in self.players:
            return self.players[ctx.guild.id]
        else:
            player = MusicPlayer(ctx)
            self.players[ctx.guild.id] = player
            return player

    @commands.command(name='현재곡', aliases=['nowplaying', 'np'])
    async def now_playing(self, ctx):
        await handle_now_playing(self, ctx)

    @commands.command(name='불러', aliases=['playfirst'])
    async def play_first(self, ctx):
        await handle_play_first(self, ctx)

    @commands.command(name='종료', aliases=['exit', 'stop'])
    async def stop(self, ctx):
        await handle_stop(self, ctx)

    @commands.command(name='나가', aliases=['leave', 'bye'])
    async def leave(self, ctx):
        await handle_leave(self, ctx)

    @commands.command(name='볼륨', aliases=['volume', 'vol'])
    async def volume(self, ctx, volume: int):
        await handle_volume(self, ctx, volume)

    @commands.command(name='재생', aliases=['play'])
    async def play(self, ctx, *, url: str):
        await handle_play(self, ctx, url)

    @commands.command(name='검색', aliases=['search', 'find'])
    async def search(self, ctx, *, query: str):
        await handle_search(self, ctx, query)

    @commands.command(name='대기열', aliases=['queue', '큐'])
    async def queue(self, ctx):
        # await handle_now_playing(self, ctx)
        await handle_queue(self, ctx)

    @commands.command(name='플레이리스트재생', aliases=['playlistplay', '리스트재생'])
    async def playlist_play(self, ctx, *urls):
        await handle_playlist_play(self, ctx, urls)

class UtilsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='도움말', aliases=['help', '도움', 'h'])
    async def help_command(self, ctx):
        await handle_help(self, ctx)