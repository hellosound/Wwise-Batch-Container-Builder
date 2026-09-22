from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ContainerType(Enum):
    RANDOM = "Random"
    SEQUENCE = "Sequence"
    BLEND = "Blend"
    ACTOR_MIXER = "ActorMixer"

    
@dataclass
class WwiseObject:
    id: str
    name: str
    type: str
    path: str
    parent_id: str | None
    parent_name: str | None


@dataclass(frozen=True)
class AudioFile:
    """A WAV selected from the filesystem but not yet imported into Wwise."""

    path: str

    @property
    def name(self) -> str:
        return Path(self.path).stem


class PlanAction(Enum):
    CREATE = "Create"
    REUSE = "Reuse"
    SKIP = "Skip"

@dataclass
class GroupPlan:
    """Validated instructions for one grouped source set."""

    group_name: str
    parent_id: str
    container_type: ContainerType
    action: PlanAction
    objects: list[WwiseObject] = field(default_factory=list)
    files: list[AudioFile] = field(default_factory=list)
    parent_name: str | None = None
    parent_path: str | None = None
    existing_container_id: str | None = None
    skip_reason: str | None = None

    @property
    def count(self) -> int:
        return len(self.objects) + len(self.files)

    @property
    def is_file_import(self) -> bool:
        return bool(self.files)
