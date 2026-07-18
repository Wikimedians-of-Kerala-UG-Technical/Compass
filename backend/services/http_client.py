import requests

session = requests.Session()
session.headers.update({
    "User-Agent": "WikiTaskPro/0.1 (https://github.com/your-org/wikitask-pro; contact@example.com)"
})
