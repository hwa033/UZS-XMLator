"""
Domain layer: Business logic, configuration, and data models.
Pure Python - no Flask dependencies.
"""

import datetime
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ============================================================================
# STRUCTURED LOGGING
# ============================================================================


class StructuredLogger:
    """JSON-structured logging with context"""

    def __init__(self, name: str, log_file: Optional[Path] = None):
        self.name = name
        self.logger = logging.getLogger(name)
        self.log_file = log_file

    def info(self, event: str, **context):
        """Log info event with context"""
        self._log("INFO", event, context)

    def warning(self, event: str, **context):
        """Log warning with context"""
        self._log("WARNING", event, context)

    def error(self, event: str, **context):
        """Log error with context"""
        self._log("ERROR", event, context)

    def _log(self, level: str, event: str, context: dict):
        """Internal logging - outputs JSON"""
        if os.environ.get("XMLATOR_LOG_QUIET") == "1":
            quiet_events = os.environ.get(
                "XMLATOR_LOG_QUIET_EVENTS",
                "get_output_directory_start,get_output_directory_fallback,get_local_downloads_dir_chosen",
            )
            quiet_set = {e.strip() for e in quiet_events.split(",") if e.strip()}
            if event in quiet_set:
                return

        log_entry = {
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "level": level,
            "event": event,
            "logger": self.name,
            **context,
        }

        # To stdout
        print(json.dumps(log_entry, ensure_ascii=False))

        # To file if configured
        if self.log_file:
            try:
                self.log_file.parent.mkdir(parents=True, exist_ok=True)
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            except Exception:
                pass


# Global loggers
logger_domain = StructuredLogger("xmlator.domain")
logger_upload = StructuredLogger("xmlator.upload")
logger_file = StructuredLogger("xmlator.file")


# ============================================================================
# DATA MODELS
# ============================================================================


@dataclass
class ValidationResult:
    """Result of validation operation"""

    success: bool
    message: str = ""
    error_messages: list = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.error_messages is None:
            self.error_messages = []


@dataclass
class GeneratedFile:
    """Metadata about a generated XML file"""

    filename: str
    filepath: str
    tijdstip: str  # ISO format
    size: int  # bytes


class Configuration:
    """Single source of truth for application configuration"""

    ALLOWED_BERICHTYPES = ("ZBM", "VM", "OTP3", "DIGIPOORT")
    REQUIRED_EXCEL_FIELDS = ("BSN", "Voornaam", "Achternaam", "Geboortedatum")
    OPTIONAL_EXCEL_FIELDS = (
        "Loonheffingennummer",
        "Loonheffingennr",
        "IndienerNaam",
        "CdRolKetenpartij",
        "CdSrtIndiener",
        "NaamSoftwarePakket",
        "VersieSoftwarePakket",
        "BerichtkenmerkIndiener",
        "VolgNr",
        "IndArbeidsgehandicapt",
        "CdBerichtType",
    )

    # Berichttype mappings
    BERICHTTYPE_MAP = {
        "DIGIPOORT": "OTP3",
        "OTP3": "OTP3",
        "ZBM": "ZBM",
        "VM": "VM",
    }

    MAX_FILE_LIST = 25
    FILE_RETENTION_DAYS = 30
    DEFAULT_BERICHTTYPE = "ZBM"
    DEFAULT_ENVIRONMENT = "UZSTA_OMG"

    @staticmethod
    def load_from_file(config_path: Path) -> dict:
        """Load configuration from JSON file"""
        logger_domain.info("config_load_start", path=str(config_path))
        
        defaults = {
            "omgeving": Configuration.DEFAULT_ENVIRONMENT,
            "filedrop_locaties": {},
            "upload_max_size_mb": 10,
            "xsd_path": "docs/UwvZwMeldingInternBody-v0428-b01.xsd",
            "log_level": "INFO",
            "output_directory": "",
            "auto_validate": False,
            "excel_com_enabled": False,
            "default_test_indicator": "2",
            "default_fiscaal_nr": "",
            "default_loonheffing_nr": "",
            "file_retention_days": Configuration.FILE_RETENTION_DAYS,
        }

        try:
            if config_path.exists():
                with open(config_path) as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        merged = defaults.copy()
                        merged.update(data)
                        logger_domain.info("config_load_success", path=str(config_path), merged_keys=len(merged))
                        return merged
            else:
                logger_domain.warning("config_load_not_found", path=str(config_path))
        except Exception as e:
            logger_domain.error("config_load_failed", path=str(config_path), error=str(e))

        logger_domain.info("config_load_using_defaults")
        return defaults


class FiledropRouter:
    """Route files to correct filedrop directory based on berichttype and environment"""

    def __init__(self, config: dict):
        self.config = config
        self.filedrop_locaties = config.get("filedrop_locaties", {})
        self.override_base = os.environ.get("XMLATOR_FILEDROP_BASE")
        self.override_output = config.get("output_directory") or os.environ.get(
            "XMLATOR_OUTPUT_DIR"
        )
        self._output_cache: dict[tuple[Optional[str], Optional[str]], Path] = {}

    def get_output_directory(
        self,
        aanvraag_type: Optional[str] = None,
        omgeving: Optional[str] = None,
        quiet: bool = False,
    ) -> Path:
        """
        Determine output directory for generated files.

        Args:
            aanvraag_type: OTP3, ZBM, VM (optional)
            omgeving: Environment like UZSTA_OMG, UZSA_ACC1 (optional, uses config default)

        Returns:
            Path to output directory
        """
        if omgeving is None:
            omgeving = self.config.get("omgeving", Configuration.DEFAULT_ENVIRONMENT)

        cache_key = (aanvraag_type, omgeving)
        if cache_key in self._output_cache:
            cached = self._output_cache[cache_key]
            if cached.exists():
                if not quiet:
                    logger_domain.info(
                        "get_output_directory_cache_hit",
                        aanvraag_type=aanvraag_type,
                        omgeving=omgeving,
                        path=str(cached),
                    )
                return cached

        if not quiet:
            logger_domain.info(
                "get_output_directory_start",
                aanvraag_type=aanvraag_type,
                omgeving=omgeving,
            )

        # 1. Check explicit override
        if self.override_output:
            chosen = self._normalize_path(self.override_output)
            if self._try_create(chosen):
                if not quiet:
                    logger_domain.info(
                        "get_output_directory_override",
                        path=str(chosen),
                    )
                self._output_cache[cache_key] = chosen
                return chosen

        # 2. Check filedrop config
        if (
            aanvraag_type
            and omgeving in self.filedrop_locaties
            and self.filedrop_locaties[omgeving]
        ):
            chosen = self._find_berichttype_path(
                aanvraag_type, self.filedrop_locaties[omgeving]
            )
            if chosen:
                if not quiet:
                    logger_domain.info(
                        "get_output_directory_filedrop",
                        path=str(chosen),
                        aanvraag_type=aanvraag_type,
                        omgeving=omgeving,
                    )
                self._output_cache[cache_key] = chosen
                return chosen

        # 3. Fallback to local downloads
        fallback = self._get_local_downloads_dir()
        if not quiet:
            logger_domain.info("get_output_directory_fallback", path=str(fallback))
        self._output_cache[cache_key] = fallback
        return fallback

    def _normalize_path(self, path: str) -> Path:
        """Expand environment variables and user home"""
        expanded = os.path.expanduser(os.path.expandvars(path))
        if self.override_base:
            default_base = r"D:\\GUP\\UZS\\filedrop"
            norm_expanded = expanded.replace("\\", "/")
            norm_default = default_base.replace("\\", "/")
            norm_override = self.override_base.replace("\\", "/")
            if norm_expanded.startswith(norm_default):
                expanded = norm_override + norm_expanded[len(norm_default) :]
        return Path(expanded)

    def _try_create(self, path: Path) -> bool:
        """Try to create path, return True if successful"""
        try:
            drive, _ = os.path.splitdrive(str(path))
            if drive and not Path(drive).exists():
                return False
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger_domain.warning(
                "try_create_failed",
                path=str(path),
                error=str(e),
            )
            return False

    def _find_berichttype_path(self, berichttype: str, omg_map: dict) -> Optional[Path]:
        """Find matching path for berichttype in environment map"""
        berichttype_upper = str(berichttype).upper()

        # Exact match
        if berichttype_upper in omg_map:
            chosen = self._normalize_path(omg_map[berichttype_upper])
            if self._try_create(chosen):
                logger_domain.info(
                    "find_berichttype_path_exact",
                    berichttype=berichttype_upper,
                    path=str(chosen),
                )
                return chosen

        # ZBM/VM share location
        if berichttype_upper in ["ZBM", "VM"]:
            for key in ["ZBM", "VM"]:
                if key in omg_map:
                    chosen = self._normalize_path(omg_map[key])
                    if self._try_create(chosen):
                        logger_domain.info(
                            "find_berichttype_path_shared",
                            berichttype=berichttype_upper,
                            resolved_key=key,
                            path=str(chosen),
                        )
                        return chosen

        # OTP3/DIGIPOORT share location
        if berichttype_upper in ["DIGIPOORT", "OTP3"]:
            for key in ["OTP3", "DIGIPOORT"]:
                if key in omg_map:
                    chosen = self._normalize_path(omg_map[key])
                    if self._try_create(chosen):
                        logger_domain.info(
                            "find_berichttype_path_shared",
                            berichttype=berichttype_upper,
                            resolved_key=key,
                            path=str(chosen),
                        )
                        return chosen

        return None

    def _get_local_downloads_dir(self) -> Path:
        """Get user's Downloads directory or fallback"""
        public_root = os.environ.get("PUBLIC") or r"C:\Users\Public"
        public_downloads = Path(public_root) / "Downloads"
        user_downloads = Path.home() / "Downloads"
        fallback = Path(__file__).parent / "static" / "downloads"

        for candidate in [public_downloads, user_downloads, fallback]:
            if candidate.is_dir() or self._try_create(candidate):
                logger_domain.info(
                    "get_local_downloads_dir_chosen",
                    path=str(candidate),
                )
                return candidate

        self._try_create(fallback)
        logger_domain.warning(
            "get_local_downloads_dir_fallback",
            path=str(fallback),
        )
        return fallback


class FileManager:
    """Manage listing, pruning, and deleting generated files"""

    def __init__(self, router: FiledropRouter):
        self.router = router

    def list_generated_files(self, limit: int = 25, prune: bool = False) -> tuple[list[GeneratedFile], int]:
        """
        List generated XML files sorted by date (newest first).

        Args:
            limit: Maximum files to return
            prune: If True, delete oldest files beyond limit

        Returns:
            Tuple of (files list, total count)
        """
        logger_file.info("list_generated_files_start", limit=limit, prune=prune)
        
        directories = [
            self.router.get_output_directory("ZBM"),
            self.router.get_output_directory("Digipoort"),
            self.router.get_output_directory(),
        ]
        unique_dirs = list(dict.fromkeys(directories))  # Remove duplicates

        files_with_time = []
        for out_dir in unique_dirs:
            if out_dir.exists():
                for fname in out_dir.iterdir():
                    if fname.suffix == ".xml":
                        try:
                            mtime = fname.stat().st_mtime
                            files_with_time.append((fname.name, fname, mtime))
                        except Exception:
                            continue

        files_with_time.sort(key=lambda x: x[2], reverse=True)
        total_count = len(files_with_time)

        # Prune if needed
        pruned_count = 0
        if prune and total_count > limit:
            for fname, fpath, _ in files_with_time[limit:]:
                try:
                    fpath.unlink()
                    pruned_count += 1
                except Exception as e:
                    logger_file.warning("list_generated_files_prune_failed", filename=fname, error=str(e))

        # Limit results
        files_with_time = files_with_time[:limit]

        # Build result
        result = []
        for fname, fpath, mtime in files_with_time:
            try:
                tijdstip = datetime.datetime.fromtimestamp(mtime).isoformat()
                size = fpath.stat().st_size
                result.append(GeneratedFile(fname, str(fpath), tijdstip, size))
            except Exception:
                continue

        logger_file.info("list_generated_files_complete", returned=len(result), total=total_count, pruned=pruned_count)
        return result, total_count

    def delete_files(self, filenames: list[str]) -> tuple[int, list[str]]:
        """
        Delete specified files.

        Args:
            filenames: List of filenames to delete

        Returns:
            Tuple of (deleted count, missing/failed filenames)
        """
        logger_file.info("delete_files_start", count=len(filenames))

        # Build file map
        directories = [
            self.router.get_output_directory("ZBM"),
            self.router.get_output_directory("Digipoort"),
            self.router.get_output_directory(),
        ]
        unique_dirs = list(dict.fromkeys(directories))

        file_map = {}
        for out_dir in unique_dirs:
            if out_dir.exists():
                for fname in out_dir.iterdir():
                    if fname.suffix == ".xml" and fname.is_file():
                        file_map[fname.name] = fname

        deleted = 0
        missing = []

        for fn in filenames:
            # Security: prevent path traversal
            if (
                not isinstance(fn, str)
                or "/" in fn
                or ".." in fn
                or not fn.endswith(".xml")
            ):
                logger_file.warning("delete_files_invalid", filename=fn)
                continue

            if fn not in file_map:
                missing.append(fn)
                continue

            try:
                file_map[fn].unlink()
                deleted += 1
                logger_file.info("file_deleted", filename=fn)
            except Exception as e:
                logger_file.error(
                    "delete_failed", filename=fn, error=str(e)
                )
                missing.append(fn)

        logger_file.info("delete_files_complete", deleted=deleted, missing=len(missing))
        return deleted, missing


class ExcelValidator:
    """Validate Excel data before processing"""

    @staticmethod
    def validate_rows(
        rows: list[dict], required_fields: Optional[list[str]] = None
    ) -> ValidationResult:
        """
        Validate Excel rows.

        Args:
            rows: List of row dictionaries
            required_fields: Required column names (defaults to REQUIRED_EXCEL_FIELDS)

        Returns:
            ValidationResult with success status and any errors
        """
        if required_fields is None:
            required_fields = list(Configuration.REQUIRED_EXCEL_FIELDS)  # type: ignore

        if not rows:
            logger_domain.warning("validate_rows_empty")
            return ValidationResult(
                success=False, message="No data rows found", error_messages=["File is empty"]
            )

        errors = []

        for i, row in enumerate(rows, start=2):  # Start at 2 (row 1 is header)
            if not isinstance(row, dict):
                errors.append(f"Row {i}: Not a dictionary")
                continue

            missing = [f for f in required_fields if not row.get(f)]
            if missing:
                errors.append(f"Row {i}: Missing {', '.join(missing)}")

            # Validate BSN
            bsn = row.get("BSN", "").strip()
            if bsn and (not bsn.isdigit() or len(bsn) not in (8, 9)):
                errors.append(f"Row {i}: Invalid BSN '{bsn}' (must be 8-9 digits)")

            # Validate Geboortedatum
            geb_datum = row.get("Geboortedatum", "").strip()
            if geb_datum:
                if len(geb_datum) != 8 or not geb_datum.isdigit():
                    errors.append(
                        f"Row {i}: Invalid Geboortedatum '{geb_datum}' (must be YYYYMMDD)"
                    )
                else:
                    try:
                        year, month, day = int(geb_datum[:4]), int(geb_datum[4:6]), int(
                            geb_datum[6:8]
                        )
                        datetime.datetime(year, month, day)
                    except Exception:
                        errors.append(
                            f"Row {i}: Invalid Geboortedatum '{geb_datum}' (invalid date)"
                        )

        if errors:
            logger_domain.warning(
                "validate_rows_failed",
                total_rows=len(rows),
                error_count=len(errors)
            )
            return ValidationResult(
                success=False,
                message=f"Validation failed: {len(errors)} error(s)",
                error_messages=errors,
            )

        logger_domain.info("validate_rows_success", total_rows=len(rows))
        return ValidationResult(success=True, message="All rows valid")

    @staticmethod
    def normalize_berichttype(berichttype: Optional[str]) -> str:
        """Normalize berichttype to standard form"""
        if not berichttype:
            logger_domain.warning(
                "normalize_berichttype_missing",
                fallback=Configuration.DEFAULT_BERICHTTYPE,
            )
            return Configuration.DEFAULT_BERICHTTYPE

        normalized = Configuration.BERICHTTYPE_MAP.get(
            str(berichttype).upper(), str(berichttype).upper()
        )
        if normalized not in Configuration.ALLOWED_BERICHTYPES:
            logger_domain.warning(
                "normalize_berichttype_invalid",
                input=str(berichttype),
                normalized=str(normalized),
                fallback=Configuration.DEFAULT_BERICHTTYPE,
            )
            return Configuration.DEFAULT_BERICHTTYPE

        return normalized
