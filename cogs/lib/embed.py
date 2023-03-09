from typing import Any

import discord
from discord import Colour, Embed, TextChannel

__all__ = ("Embed",)


class Embed:
    @classmethod
    def error(cls, text: str):
        e = discord.Embed(colour=Colour.red(), description=text)
        e.add_field(
            name="困った事のサポートはサポートサーバーで受付ています！", value="https://discord.gg/PR7XzhtcGB"
        )

        return e

    @classmethod
    def normal(
        cls,
        *,
        title: str = None,
        desc: str = None,
        color: Colour = None,
        colour: Colour = None,
        url: str = None
    ):

        e: discord.Embed = discord.Embed()

        if title:
            e.title = title

        if desc:
            e.description = desc

        if not color and not colour:
            color = Colour.from_rgb(133, 208, 243)

        if colour and not colour:
            color = colour

        e.colour = color

        if url:
            e.url = url

        return e
