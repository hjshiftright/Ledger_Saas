from typing import Dict
from pydantic import BaseModel

class NetWorthSnapshotDTO(BaseModel):
    as_of_date: str
    total_assets: float
    total_liabilities: float
    net_worth: float
    breakdown: Dict[str, float]

# Alias for API response
NetWorthResponse = NetWorthSnapshotDTO
