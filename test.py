from __future__ import annotations

from pprint import pprint

from stackexchange import API

api = API()
pprint(api.questions(50206003).answers().url)