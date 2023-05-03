from pydub import AudioSegment
from pydub.utils import audioop
from pydub.exceptions import CouldntEncodeError
from tempfile import NamedTemporaryFile
from discord.ext import tasks
import wave
import subprocess
import io
import os

def save_and_mono_wav(data: bytearray, sample_size, channels, sampling_rate):
    segment = NoFileAudioSegment(
        data,
        sample_width = sample_size // channels, #vc.decoder.SAMPLE_SIZE // vc.decoder.CHANNELS,
        frame_rate = sampling_rate, #vc.decoder.SAMPLING_RATE,
        channels = 2
    )
    segment = segment.set_channels(1)
    return segment.export(format="wav")

class VoiceCommandInterface():
    
    def __init__(self, bot, language_processor):
        self.bot = bot
        self.language_processor = language_processor
        self.commands = {}
        self.active_tasks = []
    
    def voice_command(self,function):
        """
        Decorator for registering function as a voice command.
        """
        print("decorator triggered")
        self.add_command(function)
        def wrapper(*args, **kwargs):
            return args
        return wrapper

    async def start_listening(self, ctx, vc, sink, user_id, interval=3):
        
        @tasks.loop(seconds=interval)
        async def listening_task():
            try:
                data = sink.read(user_id)
            except KeyError:
                return
            
            wf = save_and_mono_wav(
                data, 
                vc.decoder.SAMPLE_SIZE,
                vc.decoder.CHANNELS,
                vc.decoder.SAMPLING_RATE
            )

            words = self.language_processor(wf, framerate=vc.decoder.SAMPLING_RATE, commands=list(self.commands.keys())).split(" ")
            command = self._map_words_to_command(words)
            if command:
                await command(ctx, vc)

        listening_task.start()
        return listening_task # call .stop() on the returned task to stop the task

    def _map_words_to_command(self, words):
        for word in words:
            command_func = self.commands.get(word)
            if command_func:
                print(f"Found command {command_func}")
                return command_func

        return None

    def add_command(self, command):
        self.commands[command.__name__] = command
        return command

class NoFileAudioSegment(AudioSegment):
    """
    Subclass to allow encoding raw data as a .wav stream without saving to a file.
    """

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)
    
    def export(self, out_f=None, format='wav', codec=None, bitrate=None, parameters=None):
        """
        Overwritten export method that saves the .wav encoded data
        to a BytesIO stream rather than a file, and removes unnecessary code for our purpose
        """

        out_f = io.BytesIO()
        out_f.seek(0)

        # wav with no ffmpeg parameters can just be written directly to out_f
        easy_wav = format == "wav" and codec is None and parameters is None

        if easy_wav:
            data = out_f
        else:
            data = NamedTemporaryFile(mode="wb", delete=False)

        pcm_for_wav = self._data
        if self.sample_width == 1:
            # convert to unsigned integers for wav
            pcm_for_wav = audioop.bias(self._data, 1, 128)

        wave_data = wave.open(data, 'wb')
        wave_data.setnchannels(self.channels)
        wave_data.setsampwidth(self.sample_width)
        wave_data.setframerate(self.frame_rate)
        # For some reason packing the wave header struct with
        # a float in python 2 doesn't throw an exception
        wave_data.setnframes(int(self.frame_count()))
        wave_data.writeframesraw(pcm_for_wav)
        wave_data.close()

        # for easy wav files, we're done (wav data is written directly to out_f)
        if easy_wav:
            out_f.seek(0)
            return out_f

        output = NamedTemporaryFile(mode="w+b", delete=False)

        # build converter command to export
        conversion_command = [
            self.converter,
            '-y',  # always overwrite existing files
            "-f", "wav", "-i", data.name,  # input options (filename last)
        ]

        if codec is None:
            codec = self.DEFAULT_CODECS.get(format, None)

        if codec is not None:
            # force audio encoder
            conversion_command.extend(["-acodec", codec])

        if bitrate is not None:
            conversion_command.extend(["-b:a", bitrate])

        if parameters is not None:
            # extend arguments with arbitrary set
            conversion_command.extend(parameters)

        conversion_command.extend([
            "-f", format, output.name,  # output options (filename last)
        ])

        # read stdin / write stdout
        with open(os.devnull, 'rb') as devnull:
            p = subprocess.Popen(conversion_command, stdin=devnull, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p_out, p_err = p.communicate()

        try:
            if p.returncode != 0:
                raise CouldntEncodeError(
                    "Encoding failed. ffmpeg/avlib returned error code: {0}\n\nCommand:{1}\n\nOutput from ffmpeg/avlib:\n\n{2}".format(
                        p.returncode, conversion_command, p_err.decode(errors='ignore') ))

            output.seek(0)
            out_f.write(output.read())

        finally:
            data.close()
            output.close()
            os.unlink(data.name)
            os.unlink(output.name)

        out_f.seek(0)
        return out_f