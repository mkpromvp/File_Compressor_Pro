import requests
from bs4 import BeautifulSoup

out = []

with open("files/links.txt") as f:
links = [x.strip() for x in f if x.strip()]

for url in links:
print("Checking:", url)
try:
r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
ct = r.headers.get("content-type","")

    if any(x in url.lower() for x in [".zip",".rar",".7z",".iso"]):
        out.append(url)
        continue

    if "application" in ct:
        out.append(url)
        continue

    soup = BeautifulSoup(r.text, "html.parser")

    for a in soup.find_all("a"):
        h = a.get("href")
        if h and any(x in h for x in [".zip",".rar",".7z",".iso"]):
            out.append(h)

except Exception as e:
    print(e)

out = list(dict.fromkeys(out))

with open("files/direct.txt","w") as f:
f.write("\n".join(out))

print("FINAL:", out)
