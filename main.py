import discord
from discord.ext import commands, tasks
from voice_interface.sinks import StreamSink
from voice_interface.stt import speech_to_text
from voice_interface import VoiceCommandInterface

intents = discord.Intents.default()
intents.message_content = True

command_flag = False

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("."), 
    description='Private Bot for reliable music streaming.',
    intents= intents
)

voice_interface = VoiceCommandInterface(bot, speech_to_text)

@bot.command()
async def join(ctx):  # If you're using commands.Bot, this will also work.\
    
    sink = StreamSink()
    voice = ctx.author.voice

    vc = await voice.channel.connect()  # Connect to the voice channel the author is in.

    vc.start_recording(
        sink,
        lambda x, y: x, # Pass false callback since we don't need one (will error - not a coroutine, but we don't care)
        ctx.channel
    )

    await voice_interface.start_listening(ctx, vc, sink, ctx.author.id)
    await ctx.send('Started listening')

@voice_interface.voice_command
async def leave(ctx, vc):
    await ctx.send("Ok, leaving!")
    await vc.disconnect()

if __name__ == "__main__":
    bot.run("")

