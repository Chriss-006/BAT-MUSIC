import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import os

# Dizionario per la funzione repeat
repeat_all = {}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ {bot.user} è online!")
    try:
        synced = await bot.tree.sync()
        print(f"🔧 Comandi slash sincronizzati: {len(synced)}")
    except Exception as e:
        print(f"❌ Errore sync: {e}")

# /play
@bot.tree.command(name="play", description="Riproduce una canzone da YouTube (titolo o link)")
async def play(interaction: discord.Interaction, query: str):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("❗ Devi essere in un canale vocale!", ephemeral=True)
        return

    await interaction.response.defer()

    channel = interaction.user.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)

    if not voice_client:
        voice_client = await channel.connect()
    elif voice_client.channel != channel:
        await voice_client.move_to(channel)

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'default_search': 'ytsearch'
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            if 'entries' in info:
                info = info['entries'][0]
            url = info['url']
            title = info.get('title', 'Sconosciuto')
    except Exception as e:
        await interaction.followup.send(f"❌ Errore nella ricerca: {e}", ephemeral=True)
        return

    source = discord.FFmpegPCMAudio(url)
    voice_client.play(
        discord.PCMVolumeTransformer(source),
        after=lambda e: on_song_end(interaction.guild.id, voice_client, url)
    )

    await interaction.followup.send(f"▶️ Riproduzione: **{title}**")

# /stop
@bot.tree.command(name="stop", description="Ferma la musica")
async def stop(interaction: discord.Interaction):
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await interaction.response.send_message("🛑 Musica fermata!")
    else:
        await interaction.response.send_message("❌ Nessuna musica in riproduzione.", ephemeral=True)

# /volume
@bot.tree.command(name="volume", description="Imposta il volume (0.0 - 2.0)")
async def volume(interaction: discord.Interaction, value: float):
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_playing():
        if not isinstance(voice_client.source, discord.PCMVolumeTransformer):
            voice_client.source = discord.PCMVolumeTransformer(voice_client.source)
        voice_client.source.volume = value
        await interaction.response.send_message(f"🔊 Volume impostato a {value}")
    else:
        await interaction.response.send_message("❌ Nessuna musica in riproduzione.", ephemeral=True)

# /repeat
@bot.tree.command(name="repeat", description="Attiva/disattiva il repeat")
async def repeat(interaction: discord.Interaction):
    gid = interaction.guild.id
    repeat_all[gid] = not repeat_all.get(gid, False)
    stato = "🟢 Attivato" if repeat_all[gid] else "🔴 Disattivato"
    await interaction.response.send_message(f"🔁 Repeat: {stato}")

# Funzione repeat
def on_song_end(guild_id, voice_client, url):
    if repeat_all.get(guild_id, False):
        source = discord.FFmpegPCMAudio(url)
        voice_client.play(
            discord.PCMVolumeTransformer(source),
            after=lambda e: on_song_end(guild_id, voice_client, url)
        )

# Avvio del bot
token = os.environ.get("DISCORD_TOKEN")
if not token:
    print("❌ Errore: variabile DISCORD_TOKEN mancante su Railway")
else:
    bot.run(token)
