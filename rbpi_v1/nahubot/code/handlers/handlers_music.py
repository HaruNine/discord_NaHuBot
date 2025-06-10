from utils.utils import delete_after_delay, delete_user_command
from uiux.music_player import MusicPlayer
from uiux.music_embeds import make_player_embed, make_queue_embed, make_search_embed
import re
import yt_dlp
import discord
from discord.ui import Button, View
import asyncio
from utils.youtube_utils import ffmpeg_path, get_ydl_opts, fetch_youtube_oembed_infos, fetch_youtube_oembed_thumbnails
import os
import json
import aiohttp

async def handle_now_playing(self, ctx):
    player = self.get_player(ctx)
    now_playing_info = await player.now_playing()
    queue_list = list(player.queue._queue)
    url_items = []
    for item in queue_list:
        if isinstance(item, dict) and 'url' in item:
            url_items.append(item['url'])
        elif isinstance(item, str):
            url_items.append(item)
        else:
            url_items.append(None)
    valid_urls = [u for u in url_items if u]
    oembed_infos = await fetch_youtube_oembed_infos(valid_urls) if valid_urls else []
    queue_info = ""
    info_index = 0
    for i, item in enumerate(url_items):
        if item is None:
            queue_info += f'{i+1}. 알 수 없는 곡\n'
        else:
            info = oembed_infos[info_index]
            queue_info += f'{i+1}. {info["title"]}\n{info["url"]}\n'
            info_index += 1
    if not queue_info:
        queue_info = "바다가 대기 중이에요! 노래를 더 불러주시면 신나게 불러드릴게요~"
    embed = make_player_embed(now_playing_info, queue_info, player.loop, player.queue_loop, int(player.volume*100))
    embed.set_thumbnail(url="attachment://nahusearch.png")
    msg = await ctx.send(embed=embed, file=discord.File("/app/temp/nahusearch.png", filename="nahusearch.png"))
    await delete_after_delay(ctx, msg)

async def handle_play_first(self, ctx):
    player = self.get_player(ctx)
    if not player:
        msg = await ctx.send("바다가 아직 준비가 덜 됐어요! 음성 채널에 먼저 불러주세요~")
        await delete_after_delay(ctx, msg)
        return
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
        else:
            msg = await ctx.send("바다가 어디로 가야 할지 모르겠어요! 음성 채널에 먼저 불러주세요~")
            await delete_after_delay(ctx, msg)
            return
    await player.play_next()
    await delete_after_delay(ctx)

async def handle_stop(self, ctx):
    player = self.get_player(ctx)
    await player.stop()
    msg = await ctx.send("바다가 음악을 멈추고 음성 채널에서 빠져나왔어요! 다음에 또 불러주세요~")
    await delete_after_delay(ctx, msg)

async def handle_leave(self, ctx):
    await handle_stop(ctx)
    await delete_after_delay(ctx)

async def handle_volume(self, ctx, volume: int):
    if ctx.voice_client is None:
        msg = await ctx.send("바다가 아직 음성 채널에 없어요! 먼저 불러주시면 귀를 쫑긋 세울게요~")
        await delete_after_delay(ctx, msg)
        return
    player = self.get_player(ctx)
    if 0 <= volume <= 100:
        player.volume = volume / 100
        ctx.voice_client.source.volume = player.volume
        msg = await ctx.send(f"바다가 볼륨을 {volume}%로 맞췄어요! 귀가 간질간질~")
    else:
        msg = await ctx.send("바다가 깜짝 놀랐어요! 볼륨은 0에서 100 사이로만 조절할 수 있어요~")
    await delete_after_delay(ctx, msg)

async def handle_play(self, ctx, url: str):
    url_pattern = re.compile(r'^(https?\:\/\/)?(www\.youtube\.com|youtu\.?be)\/.+$')
    if not url_pattern.match(url):
        msg = await ctx.send("바다가 유효한 유튜브 URL을 못 찾았어요! 다시 한 번 알려주세요~")
        await delete_after_delay(ctx, msg)
        return
    player = self.get_player(ctx)
    if not player:
        msg = await ctx.send("바다가 아직 준비가 덜 됐어요! 음성 채널에 먼저 불러주세요~")
        await delete_after_delay(ctx, msg)
        return
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
            await asyncio.sleep(1)
        else:
            msg = await ctx.send("바다가 어디로 가야 할지 모르겠어요! 음성 채널에 먼저 불러주세요~")
            await delete_after_delay(ctx, msg)
            return
    ydl_opts = get_ydl_opts('play')
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        if 'entries' in info_dict:
            entries = info_dict['entries'][:10]
            entry_urls = [entry['url'] for entry in entries]
            oembed_infos = await fetch_youtube_oembed_infos(entry_urls)
            for idx, entry in enumerate(entries):
                await player.queue.put(entry['url'])
                if player.player_message:
                    await player.update_player_message()
            # 안내 embed에 oEmbed 정보 활용
            info_lines = '\n'.join([f"{i+1}. {info['title']}\n{info['url']}" for i, info in enumerate(oembed_infos)])
            msg = await ctx.send(f"바다가 재생목록의 처음 10곡을 대기열에 추가했어요!\n\n{info_lines}")
        else:
            await player.queue.put(url)
            if player.player_message:
                await player.update_player_message()
            oembed_infos = await fetch_youtube_oembed_infos([url])
            info = oembed_infos[0]
            msg = await ctx.send(f"바다가 '{info['title']}'의 노래를 대기열에 살포시 올려놨어요!\n{info['url']}")
    if player.current is None:
        await player.play_next()
    await delete_after_delay(ctx, msg)

async def handle_search(self, ctx, query: str):
    player = self.get_player(ctx)
    if not player:
        msg = await ctx.send("바다가 아직 준비가 덜 됐어요! 음성 채널에 먼저 불러주세요~")
        await delete_after_delay(ctx, msg)
        return
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
            await asyncio.sleep(1)
        else:
            msg = await ctx.send("바다가 어디로 가야 할지 모르겠어요! 음성 채널에 먼저 불러주세요~")
            await delete_after_delay(ctx, msg)
            return
    search_message = await ctx.send("바다가 열심히 검색 중이에요! 조금만 기다려주세요~")
    ydl_opts = get_ydl_opts('search')
    filtered_entries = []
    page = 1
    while len(filtered_entries) < 6:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(f"ytsearch{page * 6}:음악 {query} 노래", download=False)
        if 'entries' not in info_dict or not info_dict['entries']:
            break
        for entry in info_dict['entries']:
            if 60 <= entry.get('duration', 0) <= 600:
                filtered_entries.append(entry)
                if len(filtered_entries) == 6:
                    break
        page += 1
    if not filtered_entries:
        await search_message.delete()
        msg = await ctx.send("바다가 아무것도 못 찾았어요... 다른 검색어로 다시 불러주세요!")
        await delete_after_delay(ctx, msg)
        return
    # oEmbed로 검색결과 정보 추출
    entry_urls = [entry['url'] for entry in filtered_entries]
    oembed_infos = await fetch_youtube_oembed_infos(entry_urls)
    embed = make_search_embed(filtered_entries, oembed_infos)
    view = View()
    button_list = []
    for i, (entry, info) in enumerate(zip(filtered_entries, oembed_infos)):
        button = Button(label=f"{i+1}번 재생", style=discord.ButtonStyle.primary)
        button_list.append(button)
        async def button_callback(interaction, entry=entry):
            try:
                for b in view.children:
                    b.disabled = True
                await interaction.response.edit_message(view=view)
                await player.queue.put(entry['url'])
                if player.player_message:
                    await player.update_player_message()
                await ctx.send(f"바다가 '{info['title']}'을(를) 대기열에 살포시 올려놨어요!\n{info['url']}", delete_after=3)
                if player.current is None:
                    await player.play_next()
                try:
                    await interaction.message.delete()
                except Exception as e:
                    await ctx.send(f"메시지 삭제 실패: {e}", delete_after=5)
                await delete_user_command(ctx)
            except Exception as e:
                await ctx.send(f"검색 버튼 처리 중 오류 발생: {e}", delete_after=10)
                try:
                    await interaction.response.defer()
                except:
                    pass
        button.callback = button_callback
        view.add_item(button)
    cancel_button = Button(label="취소", style=discord.ButtonStyle.danger)
    async def cancel_callback(interaction):
        try:
            for b in view.children:
                b.disabled = True
            await interaction.response.edit_message(view=view)
            await interaction.response.send_message("바다가 검색을 멈췄어요! 다음에 또 불러주세요~", ephemeral=True, delete_after=3)
            try:
                await interaction.message.delete()
            except Exception as e:
                await ctx.send(f"메시지 삭제 실패: {e}", delete_after=5)
            await delete_user_command(ctx)
        except Exception as e:
            await ctx.send(f"검색 취소 처리 중 오류 발생: {e}", delete_after=10)
            try:
                await interaction.response.defer()
            except:
                pass
    cancel_button.callback = cancel_callback
    view.add_item(cancel_button)
    await search_message.delete()
    msg = await ctx.send(embed=embed, view=view)

async def handle_queue(self, ctx):
    player = self.get_player(ctx)
    queue_list = list(player.queue._queue)
    if not queue_list:
        msg = await ctx.send("바다가 대기 중이에요! 노래를 더 불러주시면 신나게 불러드려요~")
        await delete_after_delay(ctx, msg)
        return
    url_items = []
    for item in queue_list[:10]:
        if isinstance(item, dict) and 'url' in item:
            url_items.append(item['url'])
        elif isinstance(item, str):
            url_items.append(item)
        else:
            url_items.append(None)
    valid_urls = [u for u in url_items if u]
    oembed_infos = await fetch_youtube_oembed_thumbnails(valid_urls)
    embed = make_queue_embed(queue_list, oembed_infos)
    msg = await ctx.send(embed=embed)
    await delete_after_delay(ctx, msg)

async def handle_playlist_play(self, ctx, urls):
    player = self.get_player(ctx)
    if not player:
        msg = await ctx.send("바다가 아직 준비가 덜 됐어요! 음성 채널에 먼저 불러주세요~")
        await delete_after_delay(ctx, msg)
        return
    if not ctx.voice_client:
        if ctx.author.voice:
            await ctx.author.voice.channel.connect()
            await asyncio.sleep(1)
        else:
            msg = await ctx.send("바다가 어디로 가야 할지 모르겠어요! 음성 채널에 먼저 불러주세요~")
            await delete_after_delay(ctx, msg)
            return
    ydl_opts = get_ydl_opts('play')
    oembed_infos = await fetch_youtube_oembed_infos(list(urls))
    for idx, url in enumerate(urls):
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            await player.queue.put(url)
            if player.player_message:
                await player.update_player_message()
    info_lines = '\n'.join([f"{i+1}. {info['title']}\n{info['url']}" for i, info in enumerate(oembed_infos)])
    msg = await ctx.send(f"바다가 선생님의 플레이리스트 곡들을 대기열에 살포시 올려놨어요!\n\n{info_lines}")
    if player.current is None:
        await player.play_next()
    await delete_after_delay(ctx, msg) 