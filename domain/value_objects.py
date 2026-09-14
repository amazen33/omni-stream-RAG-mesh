from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RequestId:
    value: str

    def __post_init__(self) -> None:
        if not self.value or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", self.value):
            raise ValueError("request id must be a non-empty safe identifier")


@dataclass(frozen=True)
class TopicName:
    value: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,249}", self.value):
            raise ValueError("invalid Kafka topic")
