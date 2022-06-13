from typing import TypedDict


class CamConfig(TypedDict, total=False):
    model: str
    threshold: int
    lag: int
    com: bool  # center of mass


class RecordConfig(TypedDict, total=False):
    folder: str
    duration: int
    fps: int


class TankConfig(TypedDict, total=False):
    show: int
    center: str
    vpath: str
    sdir: str


class CamStageConfig(CamConfig, TankConfig, total=False):
    pass