from discord import sinks
import io

class StreamAudioData(sinks.AudioData):
    def __init__(self, file):
        super().__init__(file)
    
        self.last_read_byte = 0

class StreamSink(sinks.WaveSink):
    def __init__(self, *args, filters=None):
        
        super().__init__()

    @sinks.Filters.container
    def write(self, data, user):
        if user not in self.audio_data:
            file = io.BytesIO()
            self.audio_data.update({user: StreamAudioData(file)})

        file = self.audio_data[user]
        file.write(data)

    def read(self, user_id, full=False, starting_point=0) -> bytearray:
        audio = self.audio_data.get(user_id)
        if not audio:
            raise KeyError("User not found")
        
        data = audio.file.getvalue()

        if not full:
            if not starting_point:
                starting_point = audio.last_read_byte
            data = data[starting_point:]
        
        audio.last_read_byte = len(audio.file.getvalue())

        return data
