from vosk import Model, KaldiRecognizer, SetLogLevel
import json

SetLogLevel(-1)

def speech_to_text(wf, framerate, commands=[]):
    """Just a function for taking an audio stream and retrieving words from VOSK kaldi"""
    
    model = Model(lang="en-gb")
    commands = str(commands).replace("'", '"')

    rec = KaldiRecognizer(model, framerate, 
    commands)

    transcription = []

    rec.SetWords(True)

    while True:
        data = wf.read(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            result_dict = json.loads(rec.Result())
            transcription.append(result_dict.get("text", ""))

    final_result = json.loads(rec.FinalResult())
    transcription.append(final_result.get("text", ""))

    transcription_text = ' '.join(transcription)
    return transcription_text