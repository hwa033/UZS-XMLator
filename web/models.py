"""
Pydantic models for validated Excel data.
Automatically validates on creation, with clear error messages.
"""

from datetime import datetime
from pydantic import BaseModel, field_validator, ConfigDict, Field
from typing import Optional


class ExcelRow(BaseModel):
    """Validated Excel row - required fields"""

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    BSN: str
    Voornaam: str
    Achternaam: str
    Geboortedatum: str

    # Optional fields
    Loonheffingennummer: Optional[str] = None
    Loonheffingennr: Optional[str] = None
    IndienerNaam: Optional[str] = None
    CdRolKetenpartij: Optional[str] = None
    CdSrtIndiener: Optional[str] = None
    NaamSoftwarePakket: Optional[str] = None
    VersieSoftwarePakket: Optional[str] = None
    BerichtkenmerkIndiener: Optional[str] = None
    VolgNr: Optional[str] = None
    IndArbeidsgehandicapt: Optional[str] = None
    CdBerichtType: Optional[str] = None

    @field_validator("BSN")
    @classmethod
    def validate_bsn(cls, v: str) -> str:
        """BSN must be 8-9 digits"""
        v = v.strip()
        if not v.isdigit() or len(v) not in (8, 9):
            raise ValueError(f"Invalid BSN: must be 8-9 digits, got '{v}'")
        return v

    @field_validator("Geboortedatum")
    @classmethod
    def validate_geboortedatum(cls, v: str) -> str:
        """Geboortedatum must be YYYYMMDD format"""
        v = v.strip()
        if len(v) != 8 or not v.isdigit():
            raise ValueError(
                f"Invalid Geboortedatum: must be YYYYMMDD format, got '{v}'"
            )
        # Validate actual date
        try:
            year, month, day = int(v[:4]), int(v[4:6]), int(v[6:8])
            datetime(year, month, day)
        except ValueError as e:
            raise ValueError(f"Invalid date: {e}")
        return v

    @field_validator("Voornaam", "Achternaam")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Names must not be empty"""
        v = v.strip()
        if not v or len(v) > 40:
            raise ValueError(f"Name must be 1-40 characters, got '{v}'")
        return v

    @field_validator("Loonheffingennummer", "Loonheffingennr", mode="before")
    @classmethod
    def validate_loonheffing(cls, v: Optional[str]) -> Optional[str]:
        """Loonheffingennummer should be exactly 12 digits if provided"""
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        v = str(v).strip()
        if len(v) != 12 or not v.isdigit():
            raise ValueError(
                f"Invalid Loonheffingennummer: must be exactly 12 digits, got '{v}'"
            )
        return v

    @field_validator("CdBerichtType", mode="before")
    @classmethod
    def validate_berichttype(cls, v: Optional[str]) -> Optional[str]:
        """Normalize berichttype"""
        if v is None:
            return None
        v = str(v).strip().upper()
        allowed = ("ZBM", "VM", "OTP3", "DIGIPOORT")
        if v == "DIGIPOORT":
            return "OTP3"
        if v not in allowed:
            raise ValueError(
                f"Invalid CdBerichtType: must be one of {allowed}, got '{v}'"
            )
        return v


class ExcelUploadRequest(BaseModel):
    """Excel upload request parameters"""

    model_config = ConfigDict(populate_by_name=True)

    aanvraag_type: str = "ZBM"
    validate_request: bool = Field(True, validation_alias="validate", serialization_alias="validate")

    @field_validator("aanvraag_type")
    @classmethod
    def validate_aanvraag_type(cls, v: str) -> str:
        """Normalize aanvraag type"""
        v = v.strip().upper()
        if v == "DIGIPOORT":
            return "OTP3"
        allowed = ("ZBM", "VM", "OTP3")
        if v not in allowed:
            raise ValueError(
                f"Invalid aanvraag_type: must be one of {allowed}, got '{v}'"
            )
        return v


class JsonUploadRequest(BaseModel):
    """JSON upload request parameters"""

    model_config = ConfigDict(populate_by_name=True)

    aanvraag_type: str = "ZBM"
    validate_request: bool = Field(True, validation_alias="validate", serialization_alias="validate")
    BSN: Optional[str] = None
    Geboortedatum: Optional[str] = None

    @field_validator("aanvraag_type")
    @classmethod
    def validate_aanvraag_type(cls, v: str) -> str:
        """Normalize aanvraag type"""
        v = v.strip().upper()
        if v == "DIGIPOORT":
            return "OTP3"
        allowed = ("ZBM", "VM", "OTP3")
        if v not in allowed:
            raise ValueError(
                f"Invalid aanvraag_type: must be one of {allowed}, got '{v}'"
            )
        return v

    @field_validator("BSN", mode="before")
    @classmethod
    def validate_bsn(cls, v: Optional[str]) -> Optional[str]:
        """BSN must be 8-9 digits if provided"""
        if v is None:
            return None
        v = str(v).strip()
        if v == "":
            return None
        if not v.isdigit() or len(v) not in (8, 9):
            raise ValueError(f"Invalid BSN: must be 8-9 digits, got '{v}'")
        return v

    @field_validator("Geboortedatum", mode="before")
    @classmethod
    def validate_geboortedatum(cls, v: Optional[str]) -> Optional[str]:
        """Geboortedatum must be YYYYMMDD format if provided"""
        if v is None:
            return None
        v = str(v).strip()
        if v == "":
            return None
        if len(v) != 8 or not v.isdigit():
            raise ValueError(
                f"Invalid Geboortedatum: must be YYYYMMDD format, got '{v}'"
            )
        try:
            year, month, day = int(v[:4]), int(v[4:6]), int(v[6:8])
            datetime(year, month, day)
        except ValueError as e:
            raise ValueError(f"Invalid date: {e}")
        return v
