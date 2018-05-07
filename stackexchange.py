from __future__ import annotations

from typing import Union, Dict

import requests


class Request:
    def __init__(self, path: str, parameters: dict, fetcher: Fetcher):
        self.parameters = parameters
        self.path = path
        self.fetcher = fetcher
        self._request = None

    def __getattr__(self, item):
        if item in self.fetcher.children:
            return self.fetcher.children[item].bounded(self)
        raise AttributeError

    @property
    def request(self):
        if self._request is None:
            self._request = requests.get(self.path, self.parameters)
        return self._request

    @property
    def text(self):
        return self.request.text

    @property
    def json(self):
        return self.request.json()

    @property
    def url(self):
        return self.request.url


class Fetcher:
    def __init__(self, path: str, max_number_arguments=0, min_number_arguments=0, parent: Union[API, Fetcher, Request] = None, name=None, children=None):
        self._name = name or path
        self._path = path
        self._max_number_arguments = max_number_arguments
        self._min_number_arguments = min_number_arguments
        self._parent: Union[API, Fetcher, Request] = parent
        self.children: Dict[str, Fetcher] = children or {}
        for name, child in self.children.items():
            super().__setattr__(name, child.bounded(self))

    def bounded(self, parent: Union[API, Fetcher, Request]):
        return self.__class__(self._path, self._max_number_arguments, self._min_number_arguments, parent, self._name, self.children.copy())

    def __repr__(self):
        if self._parent is None:
            return f"<unbounded {type(self).__name__} '{self._name}'>"
        else:
            return f"<bounded {type(self).__name__} '{self._name}' (bound to {self._parent})>"

    def __get__(self, instance, owner):
        if instance is None:
            return self
        elif isinstance(instance, API):
            return self.bounded(instance)
        elif isinstance(instance, Fetcher):
            return self.bounded(instance._parent)
        else:
            raise TypeError(f"Illegal Parent {type(instance)}")

    def __setattr__(self, key, value):
        if isinstance(value, Fetcher) and not key.startswith("_"):
            value = value.bounded(self)
            self.children[key] = value
        super().__setattr__(key, value)

    def __set_name__(self, owner, name):
        self._name = name

    def __call__(self, *args, **kwargs):
        if isinstance(self._parent, Request):
            kwargs["site"] = self._parent.parameters["site"]
        else:
            kwargs["site"] = self.api.site
        return Request(self.get_path(args), kwargs, self)

    def get_path(self, args):
        if len(args) > self._max_number_arguments:
            raise ValueError(f"To many arguments for '{self._name}'. Expected {self._max_number_arguments}, got {len(args)}")
        elif len(args) < self._min_number_arguments:
            raise ValueError(f"Not enough arguments for '{self._name}'. Expected {self._max_number_arguments}, got {len(args)}")
        if self._parent is None:
            raise ValueError(f"Can't fetch of unbound Fetcher '{self._name}'")
        if isinstance(self._parent, Fetcher):
            return f"{self._parent.get_path(())}/{self._path}/{';'.join(str(i) for i in args)}"
        elif isinstance(self._parent, API):
            return f"https://api.stackexchange.com{self._path}/{';'.join(str(i) for i in args)}"
        elif isinstance(self._parent, Request):
            return f"{self._parent.path}/{self._path}/{';'.join(str(i) for i in args)}"
        else:
            raise TypeError("Illegal Parent")

    @property
    def api(self):
        return self._parent if isinstance(self._parent, API) else self._parent.api


class API:
    def __init__(self, site: str = "stackoverflow"):
        self.site = site

    def __repr__(self):
        return f"{type(self).__name__}({self.site!r})"

    comments = Fetcher("/comments", 100)
    comment = Fetcher("/comments", 1, 1)

    badges = Fetcher("/badges", 100)
    badges.name = Fetcher("name")
    badges.recipients = Fetcher("/recipients")
    badges.tags = Fetcher("tags")

    questions = Fetcher("/questions", 100)
    questions.answers = Fetcher("answers")
