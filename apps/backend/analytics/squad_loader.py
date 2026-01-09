"""
Squad Configuration Loader
===========================

Loads squad configuration from various sources for ROI calculations.

Priority:
1. SQUAD_CONFIG environment variable (JSON string)
2. {project_dir}/.auto-claude/squad_config.json file
3. Default values (current hardcoded constants)

This allows the frontend to pass squad configuration to the backend
when starting builds, while maintaining backward compatibility.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from .squad_config import (
    SquadConfig,
    TimeSavingsConfig,
    PreventionValuesConfig,
    QualityMultipliersConfig,
    DEFAULT_SQUAD_CONFIG,
)

logger = logging.getLogger(__name__)


def load_squad_config_from_env() -> Optional[SquadConfig]:
    """
    Load squad config from SQUAD_CONFIG environment variable.

    The environment variable should contain a JSON string with the squad configuration.
    This is the primary method for passing squad config from frontend to backend.

    Returns:
        SquadConfig if found and valid, None otherwise.
    """
    config_json = os.environ.get("SQUAD_CONFIG")
    if not config_json:
        return None

    try:
        data = json.loads(config_json)
        config = SquadConfig.from_dict(data)
        logger.debug(f"Loaded squad config from env: {config.name}")
        return config
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse SQUAD_CONFIG env var: {e}")
        return None
    except Exception as e:
        logger.warning(f"Error loading squad config from env: {e}")
        return None


def load_squad_config_from_file(project_dir: Path) -> Optional[SquadConfig]:
    """
    Load squad config from .auto-claude/squad_config.json file.

    The frontend writes this file when starting a build with a squad selected.

    Args:
        project_dir: Project root directory

    Returns:
        SquadConfig if file exists and is valid, None otherwise.
    """
    config_path = project_dir / ".auto-claude" / "squad_config.json"

    if not config_path.exists():
        return None

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        config = SquadConfig.from_dict(data)
        logger.debug(f"Loaded squad config from file: {config.name}")
        return config
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse squad config file {config_path}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Error loading squad config from file {config_path}: {e}")
        return None


def load_squad_config_from_spec_dir(spec_dir: Path) -> Optional[SquadConfig]:
    """
    Load squad config from spec directory's project root.

    Spec directories are typically at .auto-claude/specs/XXX-name/,
    so we go up to find the project root.

    Args:
        spec_dir: Spec directory path

    Returns:
        SquadConfig if found, None otherwise.
    """
    # Navigate from spec_dir to project root
    # spec_dir: /project/.auto-claude/specs/001-feature/
    # project_dir: /project/
    project_dir = spec_dir.parent.parent.parent

    if project_dir.exists():
        return load_squad_config_from_file(project_dir)

    return None


def get_squad_config(
    project_dir: Optional[Path] = None,
    spec_dir: Optional[Path] = None
) -> SquadConfig:
    """
    Get squad config with fallback to defaults.

    This is the main entry point for getting squad configuration.
    It tries multiple sources in priority order.

    Priority:
    1. SQUAD_CONFIG environment variable (JSON string)
    2. {project_dir}/.auto-claude/squad_config.json file
    3. {spec_dir}/../../squad_config.json (derived project dir)
    4. Default values (current hardcoded constants)

    Args:
        project_dir: Project root directory (optional)
        spec_dir: Spec directory (optional, used to derive project_dir)

    Returns:
        SquadConfig with loaded or default values.
    """
    # Priority 1: Environment variable
    config = load_squad_config_from_env()
    if config:
        logger.info(f"Using squad config from env: {config.name}")
        return config

    # Priority 2: Project directory file
    if project_dir:
        config = load_squad_config_from_file(project_dir)
        if config:
            logger.info(f"Using squad config from project file: {config.name}")
            return config

    # Priority 3: Spec directory (derive project dir)
    if spec_dir:
        config = load_squad_config_from_spec_dir(spec_dir)
        if config:
            logger.info(f"Using squad config from spec dir: {config.name}")
            return config

    # Priority 4: Default values
    logger.debug("Using default squad config")
    return DEFAULT_SQUAD_CONFIG


def write_squad_config_to_project(project_dir: Path, squad: SquadConfig) -> bool:
    """
    Write squad config to project's .auto-claude directory.

    This is called by the frontend when starting a build with a squad selected.

    Args:
        project_dir: Project root directory
        squad: Squad configuration to write

    Returns:
        True if successful, False otherwise.
    """
    auto_claude_dir = project_dir / ".auto-claude"
    config_path = auto_claude_dir / "squad_config.json"

    try:
        # Ensure .auto-claude directory exists
        auto_claude_dir.mkdir(parents=True, exist_ok=True)

        # Write squad config
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(squad.to_dict(), f, indent=2)

        logger.info(f"Wrote squad config to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to write squad config to {config_path}: {e}")
        return False


def clear_squad_config_from_project(project_dir: Path) -> bool:
    """
    Remove squad config file from project.

    Call this when a project is unassigned from a squad.

    Args:
        project_dir: Project root directory

    Returns:
        True if successful (or file didn't exist), False on error.
    """
    config_path = project_dir / ".auto-claude" / "squad_config.json"

    try:
        if config_path.exists():
            config_path.unlink()
            logger.info(f"Removed squad config from {config_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to remove squad config from {config_path}: {e}")
        return False


# Convenience functions for getting specific config values

def get_hourly_rate(
    project_dir: Optional[Path] = None,
    spec_dir: Optional[Path] = None,
    seniority: Optional[str] = None,
    role: Optional[str] = None
) -> float:
    """
    Get hourly rate for a stakeholder type.

    Convenience function that loads squad config and returns the appropriate rate.

    Args:
        project_dir: Project root directory (optional)
        spec_dir: Spec directory (optional)
        seniority: Seniority level (optional)
        role: Role type (optional)

    Returns:
        Hourly rate for the stakeholder type.
    """
    config = get_squad_config(project_dir=project_dir, spec_dir=spec_dir)
    return config.get_hourly_rate(seniority, role)


def get_time_savings_config(
    project_dir: Optional[Path] = None,
    spec_dir: Optional[Path] = None
) -> Dict[str, int]:
    """
    Get time savings configuration as a dictionary.

    Convenience function that loads squad config and returns time savings.

    Args:
        project_dir: Project root directory (optional)
        spec_dir: Spec directory (optional)

    Returns:
        Dictionary mapping activity names to time savings in minutes.
    """
    config = get_squad_config(project_dir=project_dir, spec_dir=spec_dir)
    return config.time_savings.to_dict()


def get_prevention_values_config(
    project_dir: Optional[Path] = None,
    spec_dir: Optional[Path] = None
) -> Dict[str, float]:
    """
    Get prevention values configuration as a dictionary.

    Convenience function that loads squad config and returns prevention values.

    Args:
        project_dir: Project root directory (optional)
        spec_dir: Spec directory (optional)

    Returns:
        Dictionary mapping category names to prevention values in USD.
    """
    config = get_squad_config(project_dir=project_dir, spec_dir=spec_dir)
    return config.prevention_values.to_dict()


def get_quality_multipliers_config(
    project_dir: Optional[Path] = None,
    spec_dir: Optional[Path] = None
) -> QualityMultipliersConfig:
    """
    Get quality multipliers configuration.

    Convenience function that loads squad config and returns quality multipliers.

    Args:
        project_dir: Project root directory (optional)
        spec_dir: Spec directory (optional)

    Returns:
        QualityMultipliersConfig instance.
    """
    config = get_squad_config(project_dir=project_dir, spec_dir=spec_dir)
    return config.quality_multipliers
