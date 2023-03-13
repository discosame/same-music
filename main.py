from discord.ext import commands
from discord import Intents
from dotenv import load_dotenv
import os

load_dotenv()

intent = Intents.all()


TOKEN = os.environ.get("TOKEN")

extensions = ("music",)

class Main(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="sc:", intents=intent)
        self.info = {}
    
    @property
    def play_emoji(self):
        return "▶️"
    
    @property
    def pause_emoji(self):
        return "⏸️"
    
    async def setup_hook(self) -> None:
        for cog in extensions:
            await self.load_extension(f"cogs.{cog}")

        await self.tree.sync()
        
        return await super().setup_hook()
    
    
    async def on_ready(self):
        print("起動しました")
        print(self.user.name)
        
    
    
if __name__ == "__main__":
    bot = Main()
    bot.run(TOKEN)