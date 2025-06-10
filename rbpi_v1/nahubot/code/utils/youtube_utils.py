import subprocess
import asyncio
import aiohttp

def get_ffmpeg_path():
    try:
        result = subprocess.run(['which', 'ffmpeg'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"Error finding ffmpeg path: {result.stderr}")
            return "ffmpeg"
    except Exception as e:
        print(f"Exception while finding ffmpeg path: {str(e)}")
        return "ffmpeg"

ffmpeg_path = get_ffmpeg_path()

# YouTube download options
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'
}

# 목적별 yt-dlp 옵션 반환 함수
def get_ydl_opts(mode='play'):
    opts = {
        'ffmpeg_location': ffmpeg_path,
        'no_warnings': True,
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
        }],
        'lazy_playlist': True,
        'no_cache_dir': True,
        "no_warnings": True,
    }
    if mode == 'play':
        opts.update({
            'format': 'worst',
            'extract_flat': True,
            'force_generic_extractor': True,
        })
    elif mode == 'search':
        opts.update({
            "format": "worst",
            "downloader" :  "aria2c",
            'quiet': True,
            'simulate': True,        # 다운로드 없이 정보만 가져옴
            'default_search': 'ytsearch',  # 기본 검색 옵션
            'noplaylist': True,
            'geo_bypass': True,
            'no_cache_dir': True,
            'geo_bypass_country': 'KR',  # 한국에서의 검색 결과
            'extract_flat': 'in_playlist',  # Extract only metadata for playlists
            'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            }],
            'ffmpeg_location': ffmpeg_path,
            "no_warnings": True,
            'lazy_playlist': True
        })
    elif mode == 'queue':
        # queue에서는 제목만 빠르게 추출할 수 있도록 최소 정보만 가져오도록 설정
        opts.update({
            'quiet': True,          # 모든 출력 억제
            'no_warnings': True,    # 경고 메시지 숨김
            'simulate': True,        # 다운로드 없이 정보만 가져옴
        })
    return opts

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -timeout 5000000 -rw_timeout 5000000 -user_agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"'
}

async def fetch_youtube_oembed_infos(urls):
    """
    여러 유튜브 URL에 대해 oEmbed API를 병렬로 호출하여 제목/URL 정보를 반환합니다.
    Args:
        urls (list[str]): 유튜브 동영상 URL 리스트
    Returns:
        list[dict]: 각 곡의 {'title': 제목, 'url': url} 딕셔너리 리스트
    """
    async def fetch_oembed(session, url):
        api_url = f"https://www.youtube.com/oembed?url={url}&format=json"
        try:
            async with session.get(api_url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {'title': data.get('title', url), 'url': url}
        except Exception as e:
            print(f"oEmbed 오류: {e}")
        return {'title': url, 'url': url}

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_oembed(session, url) for url in urls]
        return await asyncio.gather(*tasks)

async def fetch_youtube_oembed_thumbnails(urls):
    """
    여러 유튜브 URL에 대해 oEmbed API를 병렬로 호출하여 썸네일 URL, 제목, 원본 URL을 반환합니다.
    Args:
        urls (list[str]): 유튜브 동영상 URL 리스트
    Returns:
        list[dict]: 각 곡의 {'title': 제목, 'url': url, 'thumbnail_url': 썸네일} 딕셔너리 리스트
    """
    async def fetch_oembed(session, url):
        api_url = f"https://www.youtube.com/oembed?url={url}&format=json"
        try:
            async with session.get(api_url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        'title': data.get('title', url),
                        'url': url,
                        'thumbnail_url': data.get('thumbnail_url', None)
                    }
        except Exception as e:
            print(f"oEmbed 오류: {e}")
        return {'title': url, 'url': url, 'thumbnail_url': None}

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_oembed(session, url) for url in urls]
        return await asyncio.gather(*tasks)