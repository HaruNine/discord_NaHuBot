import logging

def setup_loggers():
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.WARNING)
    ytdl_logger = logging.getLogger('yt_dlp')
    ytdl_logger.setLevel(logging.ERROR)
    logging.getLogger('discord.player').setLevel(logging.ERROR)
    return discord_logger, ytdl_logger 