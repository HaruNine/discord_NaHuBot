import os
import sys
import subprocess
import asyncio
import gc
import random
import discord
from discord.ui import Button, View
from async_timeout import timeout
import yt_dlp
from utils.youtube_utils import ytdl_format_options, ffmpeg_options, get_ffmpeg_path, fetch_youtube_oembed_infos, fetch_youtube_oembed_thumbnails
from utils.utils import clear_memory, restart_program
from uiux.music_embeds import make_player_embed, make_queue_embed, make_search_embed

ffmpeg_path = get_ffmpeg_path()

class MusicPlayer:
    def __init__(self, ctx):
        self.bot = ctx.bot
        self.guild = ctx.guild
        self.channel = ctx.channel
        self.cog = ctx.cog
        self.queue = asyncio.Queue()
        self.next = asyncio.Event()
        self.np = None
        self.volume = .2
        self.current = None
        self.loop = False
        self.queue_loop = False
        self.player_message = None  # embed+view 메시지 하나만 유지
        self.idle_timeout = 300
        self.last_activity = asyncio.Event()
        self.inactive_time = 0
        self.bot.loop.create_task(self.player_loop())
        self.bot.loop.create_task(self.register_voice_state_listener())
        self.bot.loop.create_task(self.check_idle_timeout())

    async def check_idle_timeout(self):
        while True:
            await asyncio.sleep(1)
            if not self.last_activity.is_set():
                self.inactive_time += 1
                print(f"비활동 시간: {self.inactive_time}초")
                if self.inactive_time >= self.idle_timeout:
                    await self.stop()
                    restart_program()
            else:
                self.inactive_time = 0

    def restart_program(self):
        restart_program()

    async def register_voice_state_listener(self):
        @self.bot.listen('on_voice_state_update')
        async def on_voice_state_update(member, before, after):
            self.last_activity.set()
            if before.channel is not None and after.channel is None:
                if member == self.guild.me:
                    self.queue._queue.clear()
                    self.current = None
                    self.loop = False
                    self.queue_loop = False
                    if self.player_message:
                        try:
                            await self.player_message.delete()
                        except Exception:
                            pass
                        self.player_message = None
                    return
                if len(before.channel.members) > 1:
                    return
                await self.guild.voice_client.pause()
                await asyncio.sleep(10)
                await self.stop()
                self.queue._queue.clear()
                message = await member.send("바다가 음성 채널에서 나가요. 다음에 또 불러주세요!")
                await asyncio.sleep(3)
                await message.delete()
            if after.channel is not None and member != self.guild.me:
                if len(after.channel.members) == 1:
                    await self.guild.voice_client.disconnect()
                    self.queue._queue.clear()
                    await member.send("바다가 음성 채널에서 나가요. 다음에 또 불러주세요!")
                    restart_program()

    def get_queue_list(self):
        return list(self.queue._queue)

    async def make_embed(self):
        desc = ""
        queue_list = self.get_queue_list()
        url_items = []
        for item in queue_list:
            if isinstance(item, dict) and 'url' in item:
                url_items.append(item['url'])
            elif isinstance(item, str):
                url_items.append(item)
            else:
                url_items.append(None)
        # oEmbed로 대기열 제목 추출
        valid_urls = [u for u in url_items if isinstance(u, str)]
        oembed_infos = []
        if valid_urls:
            oembed_infos = await fetch_youtube_oembed_thumbnails(valid_urls)
        oembed_idx = 0
        # 현재곡 oEmbed 썸네일
        current_url = None
        if self.current and 'webpage_url' in self.current:
            current_url = self.current['webpage_url']
        elif self.current and 'url' in self.current:
            current_url = self.current['url']
        current_thumb = None
        if current_url:
            pass
        # 현재곡
        if self.current and current_url:
            desc += f"🎶 **지금 재생 중:** `{self.current.get('title', current_url)}`\n{current_url}\n"
        elif queue_list:
            next_title = queue_list[0]['title'] if isinstance(queue_list[0], dict) and 'title' in queue_list[0] else str(queue_list[0])
            desc += f"⏳ **대기 중인 곡:** `{next_title}`\n재생 순서를 기다리고 있어요! 곧 음악이 시작됩니다~\n"
        else:
            desc += "지금은 조용해요... 바다가 노래를 기다리고 있어요! 🐳\n"
        # 대기열
        if queue_list:
            desc += "\n**대기열:**\n"
            for i, item in enumerate(queue_list[:5]):
                if isinstance(item, dict) and 'title' in item:
                    desc += f"{i+1}. `{item['title']}`\n"
                elif isinstance(item, str):
                    # oembed_infos에서 제목 꺼내기
                    if oembed_idx < len(oembed_infos):
                        desc += f"{i+1}. `{oembed_infos[oembed_idx]['title']}`\n"
                        oembed_idx += 1
                    else:
                        desc += f"{i+1}. 알 수 없는 곡\n"
                else:
                    desc += f"{i+1}. 알 수 없는 곡\n"
            if len(queue_list) > 5:
                desc += f"... (총 {len(queue_list)}곡)\n"
        else:
            if self.current and 'thumbnail' in self.current:
                desc += "\n대기열이 비어있어요!\n"
            else:
                desc += "\n대기열이 비어있어요! 바다에게 노래를 불러주세요! 🐬\n"
        desc += f"\n🔁 반복: {'ON' if self.loop else 'OFF'}   🔂 전체반복: {'ON' if self.queue_loop else 'OFF'}   🔊 볼륨: {int(self.volume*100)}%"
        embed = discord.Embed(
            title="🐳 바다의 뮤직 플레이어",
            description=desc,
            color=discord.Color.blue()
        )
        # 썸네일/이미지는 update_player_message에서 동적으로 설정
        return embed

    def make_view(self):
        view = View(timeout=None)
        play_pause = Button(label="재생/일시정지", style=discord.ButtonStyle.primary, emoji="⏯️")
        skip = Button(label="다음 노래로!", style=discord.ButtonStyle.secondary, emoji="⏭️")
        loop = Button(label="이 노래 계속 들을래요", style=discord.ButtonStyle.success if self.loop else discord.ButtonStyle.danger, emoji="🔁")
        queue_loop = Button(label="전체 반복", style=discord.ButtonStyle.success if self.queue_loop else discord.ButtonStyle.danger, emoji="🔂")
        volume_up = Button(label="더 크게!", style=discord.ButtonStyle.secondary, emoji="🔊")
        volume_down = Button(label="조금만 작게", style=discord.ButtonStyle.secondary, emoji="🔉")
        stop_button = Button(label="종료", style=discord.ButtonStyle.danger, emoji="🛑")
        async def play_pause_callback(interaction):
            if self.guild.voice_client.is_paused():
                self.guild.voice_client.resume()
            else:
                self.guild.voice_client.pause()
            await self.update_player_message()
            await interaction.response.defer()
        async def skip_callback(interaction):
            self.guild.voice_client.stop()
            await interaction.response.defer()
        async def loop_callback(interaction):
            self.loop = not self.loop
            await self.update_player_message()
            await interaction.response.defer()
        async def queue_loop_callback(interaction):
            self.queue_loop = not self.queue_loop
            await self.update_player_message()
            await interaction.response.defer()
        async def volume_up_callback(interaction):
            if self.volume < 1.0:
                self.volume = min(1.0, self.volume + 0.1)
                self.guild.voice_client.source.volume = self.volume
            await self.update_player_message()
            await interaction.response.defer()
        async def volume_down_callback(interaction):
            if self.volume > 0.0:
                self.volume = max(0.0, self.volume - 0.1)
                self.guild.voice_client.source.volume = self.volume
            await self.update_player_message()
            await interaction.response.defer()
        async def stop_callback(interaction):
            await self.stop()
            if self.player_message:
                try:
                    await self.player_message.delete()
                except Exception:
                    pass
                self.player_message = None
            await interaction.response.defer()
        play_pause.callback = play_pause_callback
        skip.callback = skip_callback
        loop.callback = loop_callback
        queue_loop.callback = queue_loop_callback
        volume_up.callback = volume_up_callback
        volume_down.callback = volume_down_callback
        stop_button.callback = stop_callback
        view.add_item(play_pause)
        view.add_item(skip)
        view.add_item(loop)
        view.add_item(queue_loop)
        view.add_item(volume_up)
        view.add_item(volume_down)
        view.add_item(stop_button)
        return view

    async def update_player_message(self):
        # 현재곡 썸네일 oEmbed로 가져오기
        now_playing = await self.now_playing()
        queue_list = self.get_queue_list()
        url_items = []
        for item in queue_list:
            if isinstance(item, dict) and 'url' in item:
                url_items.append(item['url'])
            elif isinstance(item, str):
                url_items.append(item)
            else:
                url_items.append(None)
        valid_urls = [u for u in url_items if isinstance(u, str)]
        oembed_infos = []
        if valid_urls:
            oembed_infos = await fetch_youtube_oembed_thumbnails(valid_urls)
        queue_info = ""
        oembed_idx = 0
        if queue_list:
            for i, item in enumerate(queue_list[:5]):
                if isinstance(item, dict) and 'title' in item:
                    queue_info += f"{i+1}. `{item['title']}`\n"
                elif isinstance(item, str):
                    if oembed_idx < len(oembed_infos):
                        queue_info += f"{i+1}. `{oembed_infos[oembed_idx]['title']}`\n"
                        oembed_idx += 1
                    else:
                        queue_info += f"{i+1}. 알 수 없는 곡\n"
                else:
                    queue_info += f"{i+1}. 알 수 없는 곡\n"
            if len(queue_list) > 5:
                queue_info += f"... (총 {len(queue_list)}곡)\n"
        else:
            queue_info = "지금은 조용해요... 바다가 노래를 기다리고 있어요! 🐳"
        embed = make_player_embed(now_playing, queue_info, self.loop, self.queue_loop, int(self.volume*100))
        view = self.make_view()
        file = discord.File("temp/nahusing.gif", filename="nahusing.gif")
        current_thumb_url = None
        if self.current:
            url = self.current.get('webpage_url', self.current.get('url', None))
            if url:
                oembed_infos = await fetch_youtube_oembed_thumbnails([url])
                info = oembed_infos[0]
                current_thumb_url = info.get('thumbnail_url')
        # embed에 썸네일/이미지 설정 (위치 바꿈)
        embed.set_thumbnail(url="attachment://nahusing.gif")
        if current_thumb_url:
            embed.set_image(url=current_thumb_url)
        else:
            embed.set_image(url=None)
        if self.current:
            if self.player_message:
                await self.player_message.edit(embed=embed, view=view, attachments=[file])
            else:
                self.player_message = await self.channel.send(embed=embed, view=view, file=file)
        else:
            if self.player_message:
                try:
                    await self.player_message.delete()
                except Exception:
                    pass
                self.player_message = None

    async def player_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            self.next.clear()
            self.last_activity.set()
            try:
                async with timeout(300):
                    url = await self.queue.get()  # 항상 url만 저장되어 있음
            except asyncio.TimeoutError:
                return await self.stop()
            # yt-dlp 작업 전 안내 embed 출력
            wait_msg = None
            try:
                embed = discord.Embed(
                    title="노래 정보를 불러오는 중이에요! 🎶",
                    description="바다가 곡을 준비 중이에요. 잠시만 기다려주세요~ 🐳",
                    color=discord.Color.blue()
                )
                embed.set_thumbnail(url="attachment://nahusearch.png")
                wait_msg = await self.channel.send(embed=embed, file=discord.File("/app/temp/nahusearch.png", filename="nahusearch.png"))
                # 재생 직전에 info 추출
                ydl = yt_dlp.YoutubeDL(ytdl_format_options)
                info = await self.bot.loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
            except Exception as e:
                await self.channel.send(f'어머나, 오류가 발생했어요: {str(e)} 😢')
                if wait_msg:
                    await wait_msg.delete()
                continue
            if wait_msg:
                await wait_msg.delete()
            self.current = info
            await self.update_player_message()
            try:
                self.guild.voice_client.play(
                    discord.FFmpegPCMAudio(info['url'], executable=ffmpeg_path, before_options=ffmpeg_options['before_options'], options=ffmpeg_options['options']),
                    after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set)
                )
                self.guild.voice_client.source = discord.PCMVolumeTransformer(self.guild.voice_client.source)
                self.guild.voice_client.source.volume = self.volume
            except Exception as e:
                await self.channel.send(f"앗, 재생 중에 문제가 생겼어요: {str(e)}")
                continue
            await self.next.wait()
            if self.queue_loop and not self.loop:
                await self.queue.put(url)  # url만 다시 큐에 저장
            if self.queue.empty() and not (self.loop or self.queue_loop):
                self.current = None
                await self.update_player_message()
                await self.stop()
                break
            self.current = None
            await self.update_player_message()

    async def stop(self):
        self.queue._queue.clear()
        await self.clear_memory()
        if self.guild.voice_client:
            await self.guild.voice_client.disconnect()
            restart_program()
        self.current = None
        self.loop = False
        self.queue_loop = False
        if self.player_message:
            try:
                await self.player_message.delete()
            except Exception:
                pass
            self.player_message = None

    async def clear_memory(self):
        clear_memory()

    def destroy(self, guild):
        return self.bot.loop.create_task(self.cog.cleanup(guild))

    async def play_next(self):
        while True:
            if self.queue.empty():
                return
            if self.loop:
                source = self.current
            else:
                source = await self.queue.get()
            if self.guild.voice_client is None:
                if self.channel.members:
                    await self.channel.connect()
                else:
                    return
            if self.loop:
                await self.queue.put(source)
            self.guild.voice_client.play(
                discord.FFmpegPCMAudio(source['url'], executable=ffmpeg_path, before_options=ffmpeg_options['before_options'], options=ffmpeg_options['options']),
                after=lambda _: self.bot.loop.call_soon_threadsafe(self.next.set)
            )
            if self.current is None and not self.queue.empty():
                await self.play_next()

    async def now_playing(self):
        if self.current:
            # oEmbed로 제목/URL 출력
            url = self.current.get('webpage_url', self.current.get('url', None))
            if url:
                oembed_infos = await fetch_youtube_oembed_infos([url])
                info = oembed_infos[0]
                return f"🎶 지금 재생 중: {info['title']}\n{info['url']}"
            else:
                return f"🎶 지금 재생 중: {self.current.get('title', '알 수 없음')}"
        else:
            return "지금은 재생 중인 곡이 없어요!" 