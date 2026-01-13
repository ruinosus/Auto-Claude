"""
Configuration Management for ROI Engine

Loads squad configuration from project, environment, or defaults.
Provides hourly rates based on role and seniority.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .models import Role, Seniority


# Default hourly rates by seniority (USD)
DEFAULT_SENIORITY_RATES = {
    Seniority.JUNIOR: 50.0,
    Seniority.MID: 75.0,
    Seniority.SENIOR: 125.0,
    Seniority.STAFF: 175.0,
    Seniority.PRINCIPAL: 225.0,
}

# Role multipliers (relative to developer baseline of 1.0)
DEFAULT_ROLE_MULTIPLIERS = {
    Role.DEVELOPER: 1.0,
    Role.QA: 0.9,
    Role.DEVOPS: 1.1,
    Role.PM: 0.95,
    Role.ARCHITECT: 1.2,
    Role.TECH_LEAD: 1.15,
}


@dataclass
class SquadConfigWrapper:
    """
    Wrapper around squad configuration for ROI calculations.

    Provides easy access to hourly rates based on role and seniority,
    using either project-specific config or defaults.
    """

    id: str = "default"
    name: str = "Default Squad"
    description: str = ""
    default_seniority: Seniority = Seniority.SENIOR
    default_hourly_rate: float = 150.0

    # Custom rates override: key format is "{seniority}_{role}"
    stakeholder_rates: dict[str, float] = field(default_factory=dict)

    # Source of this config
    source: str = "default"  # "project", "env", or "default"

    def get_hourly_rate(
        self,
        role: Role,
        seniority: Seniority | None = None,
    ) -> float:
        """
        Get hourly rate for a role and seniority.

        Priority:
        1. Custom stakeholder_rates if defined
        2. Calculated from seniority base × role multiplier
        3. Default hourly rate
        """
        seniority = seniority or self.default_seniority

        # Check custom rates first
        rate_key = f"{seniority.value}_{role.value}"
        if rate_key in self.stakeholder_rates:
            return self.stakeholder_rates[rate_key]

        # Calculate from base rate × multiplier
        base_rate = DEFAULT_SENIORITY_RATES.get(seniority, self.default_hourly_rate)
        multiplier = DEFAULT_ROLE_MULTIPLIERS.get(role, 1.0)

        return base_rate * multiplier

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "default_seniority": self.default_seniority.value,
            "default_hourly_rate": self.default_hourly_rate,
            "stakeholder_rates": self.stakeholder_rates,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], source: str = "unknown") -> "SquadConfigWrapper":
        """Create from dictionary (e.g., loaded from JSON)."""
        seniority_str = data.get("default_seniority", "senior")
        try:
            seniority = Seniority(seniority_str)
        except ValueError:
            seniority = Seniority.SENIOR

        return cls(
            id=data.get("id", "unknown"),
            name=data.get("name", "Unknown Squad"),
            description=data.get("description", ""),
            default_seniority=seniority,
            default_hourly_rate=data.get("default_hourly_rate", 150.0),
            stakeholder_rates=data.get("stakeholder_rates", {}),
            source=source,
        )


def load_squad_config(
    project_dir: Path | str | None = None,
    spec_dir: Path | str | None = None,
) -> SquadConfigWrapper:
    """
    Load squad configuration with fallback chain.

    Priority:
    1. SQUAD_CONFIG environment variable (JSON string)
    2. Project-level config: {project_dir}/.auto-claude/squad_config.json
    3. Spec-level config: {spec_dir}/../../squad_config.json
    4. Default configuration

    Args:
        project_dir: Project directory path
        spec_dir: Spec directory path (alternative way to find project)

    Returns:
        SquadConfigWrapper with loaded or default configuration
    """
    # Try environment variable first
    env_config = os.environ.get("SQUAD_CONFIG")
    if env_config:
        try:
            data = json.loads(env_config)
            return SquadConfigWrapper.from_dict(data, source="env")
        except json.JSONDecodeError:
            pass

    # Try project-level config
    if project_dir:
        project_path = Path(project_dir)
        config_file = project_path / ".auto-claude" / "squad_config.json"
        if config_file.exists():
            try:
                data = json.loads(config_file.read_text())
                return SquadConfigWrapper.from_dict(data, source="project")
            except (json.JSONDecodeError, OSError):
                pass

    # Try spec-level config (derive project from spec)
    if spec_dir:
        spec_path = Path(spec_dir)
        # Spec is usually at .auto-claude/specs/XXX/, so project is 3 levels up
        project_path = spec_path.parent.parent.parent
        config_file = project_path / ".auto-claude" / "squad_config.json"
        if config_file.exists():
            try:
                data = json.loads(config_file.read_text())
                return SquadConfigWrapper.from_dict(data, source="project")
            except (json.JSONDecodeError, OSError):
                pass

    # Return default config
    return SquadConfigWrapper(source="default")


def get_default_config() -> SquadConfigWrapper:
    """Get the default squad configuration."""
    return SquadConfigWrapper(source="default")


# Export rate tables for UI display
def get_rate_table() -> dict[str, dict[str, float]]:
    """
    Get complete rate table for all role/seniority combinations.

    Returns:
        Nested dict: {seniority: {role: hourly_rate}}
    """
    table = {}
    for seniority in Seniority:
        table[seniority.value] = {}
        for role in Role:
            base_rate = DEFAULT_SENIORITY_RATES[seniority]
            multiplier = DEFAULT_ROLE_MULTIPLIERS[role]
            table[seniority.value][role.value] = round(base_rate * multiplier, 2)
    return table
