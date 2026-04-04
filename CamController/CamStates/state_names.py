from enum import Enum


class StateName(str, Enum):
    INIT = "InitState"
    POST = "PostState"
    STREAM = "StreamState"
