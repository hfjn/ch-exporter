import dataclasses
from datetime import datetime
from typing import Dict, Optional


@dataclasses.dataclass
class Host:
    name: str
    port: int
    labels: Optional[Dict[str, str]] = None
    last_check: Optional[datetime] = None
    node_healthy: bool = True
    replication_healthy: bool = True

    @property
    def url(self) -> str:
        return f"http://{self.name}:{self.port}"
