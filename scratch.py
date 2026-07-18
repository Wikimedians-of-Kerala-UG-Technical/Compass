import requests

title = "Python (programming language)"
res = requests.get("https://en.wikipedia.org/w/api.php", params={
    "action": "query",
    "list": "search",
    "srsearch": title,
    "utf8": "",
    "format": "json",
    "srlimit": 3
}).json()

print(res)
