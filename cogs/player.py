import discord
import yt_dlp
import asyncio
from collections import deque

# ─────────────────────────────────────────────
#  Конфиг yt-dlp
# ─────────────────────────────────────────────
YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn -bufsize 512k",
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

# ─────────────────────────────────────────────
#  Источник аудио
# ─────────────────────────────────────────────
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data      = data
        self.title     = data.get("title", "Неизвестно")
        self.url       = data.get("webpage_url", "")
        self.duration  = data.get("duration", 0)
        self.thumbnail = data.get("thumbnail", "")

    @classmethod
    async def from_url(cls, url: str, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None,
            lambda: ytdl.extract_info(url, download=False)
        )
        if "entries" in data:
            data = data["entries"][0]
        return cls(
            discord.FFmpegPCMAudio(data["url"], **FFMPEG_OPTIONS),
            data=data
        )

# ─────────────────────────────────────────────
#  Состояние плеера (на сервер)
# ─────────────────────────────────────────────
class GuildPlayer:
    def __init__(self):
        self.queue:   deque             = deque()
        self.current: YTDLSource | None = None
        self.volume:  float             = 0.5
        self.loop:    bool              = False

# Глобальный словарь плееров
players: dict[int, GuildPlayer] = {}

def get_player(guild_id: int) -> GuildPlayer:
    if guild_id not in players:
        players[guild_id] = GuildPlayer()
    return players[guild_id]

# ─────────────────────────────────────────────
#  Хелперы
# ─────────────────────────────────────────────
def fmt_duration(sec: int) -> str:
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def now_playing_embed(source: YTDLSource) -> discord.Embed:
    embed = discord.Embed(
        title="🎵 Сейчас играет",
        description=f"**[{source.title}]({source.url})**",
        color=0x1DB954
    )
    if source.duration:
        embed.add_field(name="Длительность", value=fmt_duration(source.duration))
    if source.thumbnail:
        embed.set_thumbnail(url=source.thumbnail)
    return embed