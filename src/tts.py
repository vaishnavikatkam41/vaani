"""Step 6: text to speech (Telugu). Week 7 work.

Install: pip install gTTS
gTTS needs internet. Later we can test an offline Telugu voice.
"""


def speak(text, out_path, lang="te", slow=True):
    """Save a spoken version of `text` to an .mp3 file. slow=True is clearer for elders."""
    from gtts import gTTS
    gTTS(text=text, lang=lang, slow=slow).save(str(out_path))
    return out_path
