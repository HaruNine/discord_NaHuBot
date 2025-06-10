import discord

def make_player_embed(now_playing, queue_info, loop, queue_loop, volume):
    """
    뮤직플레이어 상태 embed 생성
    """
    desc = f"{now_playing}\n\n**대기열:**\n{queue_info}\n\n"
    desc += f"🔁 반복: {'ON' if loop else 'OFF'}   🔂 전체반복: {'ON' if queue_loop else 'OFF'}   🔊 볼륨: {volume}%"
    embed = discord.Embed(
        title="🐳 바다의 뮤직 플레이어",
        description=desc,
        color=discord.Color.blue()
    )
    return embed

def make_queue_embed(queue_list, oembed_infos):
    """
    대기열 embed 생성
    """
    embed = discord.Embed(title=f'바다의 대기열 목록 - 총 {len(queue_list)}곡이에요!')
    for i, info in enumerate(oembed_infos):
        embed.add_field(name=f'{i+1}. {info["title"]}', value=f'[유튜브로 이동]({info["url"]})', inline=False)
    return embed

def make_search_embed(filtered_entries, oembed_infos):
    """
    검색 결과 embed 생성
    """
    embed = discord.Embed(title="바다의 검색 결과", description="듣고 싶은 노래를 골라주세요!")
    for i, (entry, info) in enumerate(zip(filtered_entries, oembed_infos)):
        duration = entry.get('duration', 0)
        minutes, seconds = divmod(duration, 60)
        duration_str = f"{int(minutes)}분 {int(seconds)}초"
        embed.add_field(name=f"{i+1}. {info['title']}", value=f"[링크]({info['url']}) - {duration_str}", inline=False)
    return embed 