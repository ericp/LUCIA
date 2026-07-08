import pyttsx3
#Text to Speech
def speak(text):
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

