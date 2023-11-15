import dataclasses
from datetime import datetime
from typing import Dict, Optional


@dataclasses.dataclass
class Host:
    name: str
    port: int
    macros: Optional[Dict[str, str]] = None
    last_check: Optional[datetime] = None
    node_healthy: bool = True
    replication_healthy: bool = True

    @property
    def url(self) -> str:
        return f"http://{self.name}:{self.port}"

    @property
    def macro_values(self):
        return [self.macros[key] for key in sorted(self.macros.keys())]

    @property
    def macro_keys(self):
        return [key for key in sorted(self.macros.keys())]
