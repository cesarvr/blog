#!/usr/bin/python
import json

def load():
    f = open("./themes/hugo-paper/static/db/db.json", "r")
    return json.load(f)

def save(data):
    open("./themes/hugo-paper/static/db/db.json", "w").write(data)


phrase = raw_input("Phrase:")
URL = raw_input("URL:")

print(phrase)
print(URL)

db = load()

db.append({"url": URL, "phrase": phrase})

data = json.dumps(db)
save(data)



