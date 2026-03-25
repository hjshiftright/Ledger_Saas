from typing import Optional
from pydantic import BaseModel, Field
from common.enums import InstitutionType

class InstitutionCreateDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    institution_type: InstitutionType
    website_url: Optional[str] = None
    notes: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "State Bank of India",
                    "institution_type": "BANK",
                    "website_url": "https://sbi.co.in",
                    "notes": "Primary bank account",
                }
            ]
        }
    }

class InstitutionResponse(BaseModel):
    id: int
    name: str
    institution_type: InstitutionType
    website_url: Optional[str] = None
    notes: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "name": "State Bank of India",
                    "institution_type": "BANK",
                    "website_url": "https://sbi.co.in",
                    "notes": "Primary bank account",
                }
            ]
        }
    }
