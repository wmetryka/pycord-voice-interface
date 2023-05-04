import discord
from discord.ext import commands, tasks
from voice_interface.sinks import StreamSink
from voice_interface.stt import speech_to_text
from voice_interface import VoiceCommandInterface

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("."), 
    description='pycord-voice-interface example',
    intents= intents
)

# 2nd argument should be a function taking (data: io.BytesIO, framerate: int, commands: list[str]) and returning the detected words as str
voice_interface = VoiceCommandInterface(bot, speech_to_text)

@bot.command()
async def join(ctx):
    
    # Custom Sink for reading .wav encoded audio as a stream
    sink = StreamSink()
    vc = await ctx.author.voice.channel.connect() 
    
    # Regular pycord start_recording method
    vc.start_recording(
        sink,
        lambda x, y: x, #will error - not a coroutine, but we don't care
        ctx.channel
    )
    
    # Takes (ctx, voice_client, sink, user_id)
    await voice_interface.start_listening(ctx, vc, sink, ctx.author.id)
    await ctx.send('Started listening')

# Function decorated with this will be called when a word matching the function name is detected
# Should take (ctx, vc)
@voice_interface.voice_command
async def leave(ctx, vc):
    await ctx.send("Ok, leaving!")
    await vc.disconnect()

if __name__ == "__main__":
    bot.run("")

