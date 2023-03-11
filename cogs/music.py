import discord
from discord.ext import commands
from discord import VoiceClient, ui, SelectOption
import asyncio
from yt_dlp import YoutubeDL

from .lib import Embed, TicTac
import os
from datetime import datetime, timedelta


# YouTubeダウンロードオプション
ydl_opts = {
    'restrictfilenames': True,
    'outtmpl': '%(title)s.%(ext)s',
    'format': 'bestaudio/best',
    'extract_flat': True,
    'quiet': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }]
}


class Voices(VoiceClient):
    def __init__(self, bot, channel):
        super().__init__(bot, channel)
        self.bot = bot
        self.items = [] 
        self.latest_number = 1
        self.edit_locked = False
        self.looped = False
        self.current_item = {}
        
    async def search_playlist(self, prompt: str):
        ydl_opts["extract_flat"] = "in_playlist"
        ydl_opts["outtmpl"] = f"songs/{self.channel.id}/%(title)s.%(ext)s"
        

        with YoutubeDL(ydl_opts) as ydl:
            playlist_results = await asyncio.to_thread(ydl.extract_info, prompt, download=False)
            played = False
            
            for i, video in enumerate(playlist_results['entries']):
                try:
                    await self.download(ydl, video["url"])
                except:
                    self.bot.dispatch("fail_download", self)
                    continue   
                self.append_item(video)
                
                if i == 0 and not self.is_playing():
                    self.bot.loop.create_task(self.play())
                    played = True


            
            return played

    async def search_video(self, prompt: str):
        played = False
        ydl_opts["outtmpl"] = f"songs/{self.channel.id}/%(title)s.%(ext)s"

        with YoutubeDL(ydl_opts) as ydl:
            video = await asyncio.to_thread(ydl.extract_info, prompt, download=False)
            video["url"] = prompt
            
            self.append_item(video)
            await self.download(ydl, video["url"])
            return played

    async def search_title(self, prompt: str):
        played = False
        ydl_opts["outtmpl"] = f"songs/{self.channel.id}/%(title)s.%(ext)s"
        
        with YoutubeDL(ydl_opts) as ydl:
            search_results =await asyncio.to_thread(ydl.extract_info, f"ytsearch:{prompt}", download=False)
            video = search_results['entries'][0]
            print(video)

            self.append_item(video)

            await self.download(ydl, video["url"])
        
        return played
            
    
    async def download(self, ytdl: YoutubeDL, url: str):
        await asyncio.to_thread(ytdl.download, url)
        
    async def put(self, prompt):
        if "playlist" in prompt:
            played = await self.search_playlist(prompt)
        
        elif "youtube.com" in prompt:
            played - await self.search_video(prompt)
        else:
            played = await self.search_title(prompt)
            
        return played


    def append_item(self, video: dict):
        start_time = discord.utils.utcnow()
        self.items.append(
            {
                "channel_name": video["channel"],
                "video_title": video["title"],
                "video_url": video["url"],
                "thumbnail_url": video["thumbnails"][-1]["url"],
                "filename": f"songs/{self.channel.id}/{video['title']}.mp3",
                "duration": video["duration"],
                "start_time": start_time,
                "end_time": start_time + timedelta(seconds=video["duration"])
            }
        )
    
        
    async def play(self):
        if not self.items:
            await self.disconnect()
            return
        self.edit_locked = True

        next_song_info = self.items.pop(0)
        
        if self.looped:
            self.items.append(
                next_song_info
            )

        self.play_start_time: datetime = discord.utils.utcnow()

        self.current_item[self.channel.id] = next_song_info

        self.bot.dispatch("send_log_next_song", self, next_song_info)
        try:
            super().play(discord.FFmpegPCMAudio(next_song_info["filename"]))
        except:
            print("play error")
            e = Embed.error(f"{next_song_info['video_title']}を再生できませんでした\n(現在修正不可能)")
            await self.bot.info[self.channel.id]["latest_message"].channel.send(embeds=[e], delete_after=15)
            self.bot.dispatch("play_next_song", self)
            return

        await asyncio.sleep(3)
    
        self.edit_locked = False
    
        while self.is_playing() or self.is_paused():
            await asyncio.sleep(1)
            
        await asyncio.sleep(2)
        
        while self.is_paused():
            await asyncio.sleep(1)
        
        try:
            if not self.looped:
                os.remove(next_song_info["filename"])
        except:
            pass
        
        self.bot.dispatch("play_next_song", self)
        

    async def disconnect(self):
        info = self.bot.info[self.channel.id]
        self.bot.info[self.channel.id]["client"].items = {}
        import shutil
        try:
            shutil.rmtree(f'songs/{self.channel.id}/')
        except:
            return
        
        try:
            await info["latest_message"].delete()
        except:
            pass
        
        await super().disconnect(force=True)
        
    
    async def pause(self):
        super().pause()
        info = self.bot.info[self.channel.id]
        lastest_message: discord.Message = info["latest_message"]
        e = lastest_message.embeds[0]
        e.set_field_at(EmbedFIeld.status, name="ステータス", value=f"{self.bot.pause_emoji} 再生停止中")
        
        try:
            await lastest_message.edit(embeds=[e])
        except:
            pass
    
    async def resume(self):
        super().resume()
        info = self.bot.info[self.channel.id]
        lastest_message: discord.Message = info["latest_message"]
        e = lastest_message.embeds[0]
        e.set_field_at(EmbedFIeld.status, name="ステータス", value=f"{self.bot.play_emoji} 再生中")
        
        try:
            await lastest_message.edit(embeds=[e])
        except:
            pass
    
    async def skip(self):
        super().stop()
        info = self.bot.info[self.channel.id]
        lastest_message: discord.Message = info["latest_message"]

        try:
            await lastest_message.delete()
        except:
            pass
        
    async def loop_enable(self):
        self.looped = True
        self.items.append(self.current_item[self.channel.id])
        
        view = TicTac()
        
        e = Embed.normal(title="現在の曲を含めてループしますか？", desc=f"⭕ -> 含める\n❌ -> 含めない")
        
        info = self.bot.info[self.channel.id]
        
        m = await info["latest_message"].channel.send(embeds=[e], view=view)
        
        await view.wait()
        
        latest_message = info["latest_message"]
        
        embed = latest_message.embeds[0]
        
        embed.set_field_at(EmbedFIeld.loop_status, name="ループステータス", value="有効中")
        
        target_field = embed.fields[EmbedFIeld.songs]
        title = self.current_item[self.channel.id]['video_title']
        
        values= target_field.values or "" + f"\n{title}\nーーーーーーーーーーーーー\n"
        
        embed.set_field_at(EmbedFIeld.songs, name="追加済み曲一覧 (再生中の曲は除外されます)", value=values)
        
        try:
            await latest_message.edit(embeds=[embed])
        except:pass        
        
        if not view.value:
            self.items.pop(-1)
            
        e = Embed.normal(desc="ループを有効にしました")
        await info["latest_message"].channel.send(embeds=[e], delete_after=15)
    
    
    async def loop_disable(self):
        self.looped = False     
        info = self.bot.info[self.channel.id]
        
        latest_message = info["latest_message"]
        
        embed = latest_message.embeds[0]
        
        embed.set_field_at(EmbedFIeld.loop_status, name="ループステータス", value="無効中")
        try:
            await latest_message.edit(embeds=[embed])
        except:pass  
            
        e = Embed.normal(desc="ループを無効にしました")
        await info["latest_message"].channel.send(embeds=[e], delete_after=15)
        

def get_h_m_s(td):
    m, s = divmod(td.seconds, 60)
    h, m = divmod(m, 60)
    return h, m, s


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot =bot
        
    @commands.hybrid_command(name="音楽再生")
    async def cmd_play(self, ctx: commands.Context, prompt: str ,voice_channel: discord.VoiceChannel = None):
        """曲を再生します"""
        
        await ctx.defer()
        
        if not (voice_channel) and not (ctx.author.voice):
            e = discord.Embed(description="VCに接続してからコマンドを実行してね")
            return await ctx.send(embeds=[e])
        
        voice_channel = voice_channel or ctx.author.voice.channel
        self.bot.info[voice_channel.id] = {}
        
        voices = await voice_channel.connect(cls=Voices)
        
        e = Embed.normal( desc="曲をYoutubeから取得しています...")
        
        mes = await ctx.send(embeds=[e])

        
        self.bot.info[voice_channel.id] = {
            "logpanel": mes,
            "client": voices,
            "owner": ctx.author,
            "edit": False,
            "owner_only": False,
            "latest_message": mes
        }
        
        self.bot.info[voice_channel.id]["logpanel"] = mes
        
        self.bot.info[voice_channel.id]["client"] = voices
        played = await voices.put(prompt)

        if not played:
            await voices.play()
    
    @commands.hybrid_command(name="音楽追加")
    async def cmd_add(self, ctx: commands.Context, prompt: str):
        """キューに曲を追加します"""
        
        await ctx.defer()
        
        if not (voice_channel := ctx.author.voice):
            e = discord.Embed(description="VCに接続してからコマンドを実行してね")
            return await ctx.send(embeds=[e])
        
        voice_client = self.bot.info[voice_channel.id]["client"]
        await voice_client.put(prompt)
    
    @commands.hybrid_command(name="一時停止")
    async def cmd_pause(self, ctx: commands.Context):
        """BOTが現在再生している曲を一時停止します"""
        
        await ctx.defer()
        
        if not (voice := ctx.author.voice):
            e = discord.Embed(description="VCに接続してからコマンドを実行してね")
            return await ctx.send(embeds=[e])
        
        info = self.bot.info[voice.channel.id]
        voice_client: Voices = info["client"]
        await voice_client.pause()
        
        self.bot.dispatch("log_edit_pause", info)
        
        
    @commands.hybrid_command(name="再生終了")
    async def cmd_stop(self, ctx: commands.Context):
        """BOTが現在再生している曲を終了して次の曲を再生します"""
        
        await ctx.defer()
        
        if not (voice := ctx.author.voice):
            e = discord.Embed(description="VCに接続してからコマンドを実行してね")
            return await ctx.send(embeds=[e])
        
        info = self.bot.info[voice.channel.id]
        voice_client: Voices = info["client"]
        await voice_client.stop()
        

    @commands.hybrid_command(name="再生再開")
    async def cmd_resume(self, ctx: commands.Context):
        """BOTが現在再生を停止している曲を再開します"""
        
        await ctx.defer()
        
        if not (voice := ctx.author.voice):
            e = discord.Embed(description="VCに接続してからコマンドを実行してね")
            return await ctx.send(embeds=[e])
        info = self.bot.info[voice.channel.id]
        voice_client: Voices = info["client"]
        await voice_client.resume()


    @commands.hybrid_command(name="退出")
    async def cmd_disconnect(self, ctx: commands.Context):
        """BOTをVCから退出させます"""
        
        await ctx.defer()
        
        if not (voice := ctx.author.voice):
            e = discord.Embed(description="VCに接続してからコマンドを実行してね")
            return await ctx.send(embeds=[e])
        
        info = self.bot.info[voice.channel.id]
        voice_client: Voices = info["client"]
        await voice_client.disconnect()


    @commands.Cog.listener()
    async def on_play_next_song(self, voice_client):
        await voice_client.play()
        
    @commands.Cog.listener()
    async def on_send_log_next_song(self, voice_client: Voices, next_info):
        cog_voice_client = self.bot.info[voice_client.channel.id]
        
        e  = Embed.normal(
            title="このメッセージは削除しないでください",
            desc=f"[{next_info['video_title']}]({next_info['video_url']})を再生しています♪"
        )
        e.set_thumbnail(url=next_info["thumbnail_url"])        
        duration = next_info["duration"]
        
        end_time = discord.utils.utcnow() + timedelta(seconds=duration)
        
        h, m,s  =get_h_m_s(timedelta(seconds=duration))
        e.add_field(
            name="再生時間-再生終了時間",
            value=f"{h}時間{m}分{s}秒  - {discord.utils.format_dt(end_time)}",
            inline=False
        )
        
        e.add_field(
            name="再生ステータス",
            value=f"{self.bot.play_emoji} 再生中",
        )
        e.add_field(
            name="ループステータス",
            value=f"{'有効中' if voice_client.looped else '無効中'}",
        )
        
        e.add_field(name="プレイリストについて", value="プレイリストの曲を全て取得するのは時間がかかるためスキップや削除をしたい場合は、反映されるまで暫くお待ちください", inline=False)
        
        value = ""
        
        for item in voice_client.items:
            value += f"{item['video_title']}\nーーーーーーーーーーーーー\n"

        e.add_field(name="追加済み曲一覧 (再生中の曲は除外されます)", value=value)
        
        view = ADDSONGView()

        if cog_voice_client["edit"]:

            logpanel = cog_voice_client["logpanel"]
            try:
                await logpanel.edit(embeds=[e], view=view)
            except:
                return
            
        else:
            try:
                await cog_voice_client["latest_message"].delete()
            except:
                pass
            
            m = await cog_voice_client["latest_message"].channel.send(embeds=[e], view=view)
            self.bot.info[voice_client.channel.id]["latest_message"] = m


class InputModal(ui.Modal, title="追加する曲を入力してね！"):
    new_song = ui.TextInput(
        label="曲入力欄", placeholder="タイトル・URLのどちらかを入力してね!プレイリストも対応してるよ!"
    )
    
    async def on_submit(self, inter: discord.Interaction):
        self.value = self.new_song.value
        await inter.response.defer()
        self.stop()



class SelectSongView(ui.View):
    def __init__(self, client: Voices):
        super().__init__(timeout=None)
        
        self.voice_client= client

        options = [SelectOption(label=items["video_title"], value=i, description=items["video_url"]) for i, items in enumerate(client.items)]

        select = ui.Select(options=options)
        select.callback = self.callback
        
        self.add_item(select)
        
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        self.values = interaction.data.get("values")
        
        self.stop()


class ADDSONGView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
        
    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        custom_id = interaction.data.get("custom_id")
        if not (voice_in_bot := interaction.guild.voice_client):
            
            if custom_id == "join":
                return True
            else:
                return False
        
        if interaction.user not in voice_in_bot.channel.members:
            if custom_id == "disconnect":
                return True
            else:
                e = Embed.error("VCに接続してからボタンを押してね!")
                await interaction.response.send_message(embeds=[e])
                
                return False
            
        return True
        

    @ui.button(emoji="⏯️", label="再開")
    async def resume(self, interaction: discord.Interaction, _):
        await interaction.response.defer()
        voice_channel = interaction.user.voice.channel
        
        voice_client: Voices = interaction.client.info[voice_channel.id]["client"]
        
        await voice_client.resume()
    
    @ui.button(emoji="⏸️", label="一時停止")
    async def pause(self, interaction: discord.Interaction, _):
        await interaction.response.defer()
        voice_channel = interaction.user.voice.channel
        
        voice_client: Voices = interaction.client.info[voice_channel.id]["client"]
        
        await voice_client.pause()


    @ui.button(emoji="⏹️", label="現在の曲をスキップ")
    async def skip(self, interaction: discord.Interaction, _):
        await interaction.response.defer()
        voice_channel = interaction.user.voice.channel
        
        voice_client: Voices = interaction.client.info[voice_channel.id]["client"]
        
        await voice_client.skip()
    
    @ui.button(emoji="🔄", label="ループ")
    async def loop(self, interaction: discord.Interaction, _):
        await interaction.response.defer()
        voice_channel = interaction.user.voice.channel
        
        voice_client: Voices = interaction.client.info[voice_channel.id]["client"]
        
        if not voice_client.looped:
            await voice_client.loop_enable()
        else:
            await voice_client.loop_disable()
        


    @ui.button(row=1, emoji="🔼", label="曲追加", style=discord.ButtonStyle.green, custom_id="join")
    async def add_song(self,interaction: discord.Interaction, _):
        if not (voice := interaction.user.voice):
            e = Embed.error("VCに接続してからボタンを押してね!")
            return await interaction.response.send_message(embeds=[e])
        
        modal = InputModal()
        await interaction.response.send_modal(modal)
        
        await modal.wait()
    
        if not interaction.guild.voice_client:
            voice_client: Voices = await voice.channel.connect(cls=Voices)
            
        else:
            voice_client: Voices = interaction.client.info[voice.channel.id]["client"]
        
        e = Embed.normal(desc=f"{modal.value}をYoutubeから取得しキューに追加しています...")
        e.add_field(
            name="追加した曲が反映されない？",
            value="Youtubeから曲を取得出来次第、次の曲再生時に反映されます"
        )
                
        m = await interaction.channel.send(embeds=[e])
        
        await voice_client.put(modal.value)
        await m.delete()
        
        if not voice_client.is_playing():
            await voice_client.play()
    
    @ui.button(row=1, emoji="🔽", label="曲削除", style=discord.ButtonStyle.red)
    async def delete_song(self,interaction: discord.Interaction, _):
        if not (voice := interaction.user.voice):
            e = Embed.error("VCに接続してからボタンを押してね!")
            return await interaction.response.send_message(embeds=[e])

        if not( interaction.client.info.get(voice.channel.id)):
            e = Embed.error("まだ曲を追加して無いよ")
            return await interaction.response.send_message(embeds=[e])
        
        
        if not( voice_client := interaction.client.info[voice.channel.id].get("client")):
            e = Embed.error("まだ曲を追加して無いよ")
            return await interaction.response.send_message(embeds=[e])
        
        if not voice_client.items:
            e = Embed.error("まだ曲を追加して無いよ")
            return await interaction.response.send_message(embeds=[e])

        await interaction.response.defer()

        view = SelectSongView(voice_client)
        e = Embed.normal(desc="削除する曲を選択してね!")
        
        m = await interaction.channel.send(embeds=[e], view=view, delete_after=180)
        
        await view.wait()
        
        await m.delete()
        
        desc = ""

        for value in view.values:
            deleted_song = interaction.client.info[voice.channel.id]["client"].items.pop(int(value))
            title = deleted_song['video_title']
            url = deleted_song['video_url']
            
            desc += f"[{title}]({url})\nーーーーーーーーーーーーー\n"
        
        e = Embed.normal(title="削除した曲一覧", desc=desc)
        
        await interaction.channel.send("以下の曲を削除しました!", embeds=[e], delete_after=15)
    
    
    @ui.button(label="曲一覧更新", row=1)
    async def update_song_list(self,interaction: discord.Interaction, _):
        if not (voice := interaction.user.voice):
            e = Embed.error("VCに接続してからボタンを押してね!")
            return await interaction.response.send_message(embeds=[e])

        if not( voice_info := interaction.client.info.get(voice.channel.id)):
            e = Embed.error("まだ曲を追加して無いよ")
            return await interaction.response.send_message(embeds=[e])
        
        
        if not( voice_client := voice_info.get("client")):
            e = Embed.error("まだ曲を追加して無いよ")
            return await interaction.response.send_message(embeds=[e])
        
        if not voice_client.items:
            e = Embed.error("まだ曲を追加して無いよ")
            return await interaction.response.send_message(embeds=[e])
        
        await interaction.response.defer()
        
        if voice_client.edit_locked:
            print("locked")
            return
        
        if not (latest_message := voice_info.get("latest_message")):
            print("none latest message")
            return
        
        e: discord.Embed = latest_message.embeds[0]
        
        value = ""
        
        for item in voice_client.items:
            value += f"{item['video_title']}\nーーーーーーーーーーーーー\n"
        
        e.set_field_at(EmbedFIeld.songs, name=e.fields[EmbedFIeld.songs].name, value=value)
        
        try:
            await latest_message.edit(embeds=[e])
        except:
            pass
    
        
    @ui.button(emoji="🔀", label="シャッフル", row=1)
    async def shuffle_song(self,interaction: discord.Interaction, _):
        
        if not (voice := interaction.user.voice):
            e = Embed.error("VCに接続してからボタンを押してね!")
            return await interaction.response.send_message(embeds=[e])

        if not( (voice_info := interaction.client.info.get(voice.channel.id))):
            e = Embed.error("まだ曲を追加して無いよ")
            return await interaction.response.send_message(embeds=[e])
        
        
        if not( voice_client := interaction.client.info[voice.channel.id].get("client")):
            e = Embed.error("まだ曲を追加して無いよ")
            return await interaction.response.send_message(embeds=[e])
        
        if not voice_client.items:
            e = Embed.error("まだ曲を追加して無いよ")
            return await interaction.response.send_message(embeds=[e])
        
        await interaction.response.defer()
        
        import random
        
        random.shuffle( interaction.client.info[voice.channel.id]["client"].items)
        
        if voice_client.edit_locked:
            return
        
        if not (latest_message := voice_info.get("latest_message")):
            return
        
        e: discord.Embed = latest_message.embeds[0]
        
        value = ""
        
        for item in voice_client.items:
            value += f"{item['video_title']}\nーーーーーーーーーーーーー\n"
        
        e.set_field_at(EmbedFIeld.songs, name=e.fields[EmbedFIeld.songs].name, value=value)
        
        try:
            await latest_message.edit(embeds=[e])
        except:
            pass
    
    
    @ui.button(label="切断", row=1, custom_id="disconnect")
    async def disconnect(self,interaction: discord.Interaction, _):
        if not (vc_in_bot := interaction.guild.voice_client):
            e = Embed.error("BOTがVCに接続して無いよ")
            return await interaction.response.send_message(embeds=[e], ephemeral=True)
        
        members = [member for member in interaction.guild.voice_client.channel.members if not member.bot]
        
        voice_client = interaction.client.info[vc_in_bot.channel.id]["client"]
        
        if not members:            
            await voice_client.disconnect()
                
            return

        
        if not (voice := interaction.user.voice):
            e = Embed.error("VCに接続してからボタンを押してね!")
            return await interaction.response.send_message(embeds=[e])

        if voice.channel.id != interaction.guild.voice_client.channel.id:
            e = Embed.error("BOTが接続してるVCに接続してからボタンを押してね!")
            return await interaction.response.send_message(embeds=[e])
        await voice_client.disconnect()

from enum import IntEnum

class EmbedFIeld(IntEnum):
    play_time: int = 0
    status: int = 1
    loop_status: int = 2
    playlist_desc: int = 3
    songs: int = 4
    
        

async def setup(bot):
    await bot.add_cog(Music(bot))