import io
import traceback
from datetime import datetime
from functools import wraps

import discord


def excepter(func):
    @wraps(func)
    async def wrapped(self, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except Exception as e:
            orig_error = getattr(e, "original", e)
            error_msg = "".join(
                traceback.TracebackException.from_exception(orig_error).format()
            )
            
            print(error_msg)
            
            with io.StringIO(error_msg) as f:

                channel = self.bot.get_channel(1076829740519919626)

                now = datetime.now()
                file_name = now.strftime("%Y年%m月%d日 %H時%M分%S秒")

                args_content = "\n".join(f"{arg_content}" for arg_content in args)
                kwargs_content = "\n".join(f"{k}: {v}" for k, v in kwargs.items())

                await channel.send(
                    f"{func}\n----------\n{args_content}\n`--------------`\n{kwargs_content}",
                    file=discord.File(f, filename=f"{file_name}.txt"),
                )

    return wrapped
