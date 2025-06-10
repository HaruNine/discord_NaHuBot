from utils.utils import delete_after_delay
import discord
import asyncio

async def handle_help(self, ctx):
    embed = discord.Embed(
        title="바다가 알려주는 명령어 모음집! 🐳",
        description="바다가 할 수 있는 일들을 소개할게요! 궁금한 게 있으면 언제든 불러주세요~",
        color=0x3498db
    )
    embed.add_field(name="!!현재곡 / !!nowplaying / !!np", value="바다가 지금 부르고 있는 노래와 대기 중인 곡들을 보여드려요!", inline=False)
    embed.add_field(name="!!불러 / !!playfirst", value="대기열 맨 앞에 있는 곡을 바다가 힘차게 불러드릴게요!", inline=False)
    embed.add_field(name="!!종료", value="바다가 노래를 멈추고 조용히 음성 채널에서 빠져나갈게요~", inline=False)
    embed.add_field(name="!!나가", value="바다가 살금살금 음성 채널에서 나가요!", inline=False)
    embed.add_field(name="!!볼륨 [0~100]", value="바다가 볼륨을 조절해드릴게요! 너무 크면 귀가 아파요~", inline=False)
    embed.add_field(name="!!재생 [유튜브URL]", value="유튜브 링크의 노래를 바다가 바로 불러드려요!", inline=False)
    embed.add_field(name="!!검색 [검색어]", value="듣고 싶은 노래를 검색해서 바다가 찾아드릴게요!", inline=False)
    embed.add_field(name="!!대기열 / !!큐 / !!대기열", value="바다가 대기 중인 곡들을 한눈에 보여드려요!", inline=False)
    msg = await ctx.send(embed=embed)
    await delete_after_delay(ctx, msg, 60)