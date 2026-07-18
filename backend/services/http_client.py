import requests
from requests.adapters import HTTPAdapter

USER_AGENT = "WikiTaskPro/0.1 (https://github.com/wikitask-pro; contact@example.com)"
DEFAULT_TIMEOUT = 15


class _TimeoutAdapter(HTTPAdapter):
    def send(self, request, **kwargs):
        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
        return super().send(request, **kwargs)


session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})
session.mount("http://", _TimeoutAdapter())
session.mount("https://", _TimeoutAdapter())
