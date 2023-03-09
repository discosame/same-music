from __future__ import annotations

from discord import (ButtonStyle, CategoryChannel, ChannelType, Interaction,
                     Member, ui)

__all__ = ("TicTac", )

class TicTac(ui.View):
    def __init__(self):
        super().__init__(timeout=None)



    @ui.button(emoji="⭕", style=ButtonStyle.green)
    async def confirm(self, interaction: Interaction, button: ui.Button):
        self.value = True
        await interaction.message.delete()
        await interaction.response.defer()

        self.stop()

    @ui.button(emoji="❌", style=ButtonStyle.gray)
    async def cancel(self, interaction: Interaction, button: ui.Button):
        self.value = False
        await interaction.message.delete()
        await interaction.response.defer()

        self.stop()


class CategorySelect(ui.View):
    def __inti__(self):
        super().__init__(timeout=None)

        self.value: CategoryChannel | None = None

    @ui.select(cls=ui.ChannelSelect, channel_types=[ChannelType.category])
    async def callback(self, inter: Interaction, select: ui.ChannelSelect):
        await inter.response.defer()

        self.value = select.values[0]

        self.stop()
