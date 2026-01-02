"""
Authentication helpers for Auto Claude.

Provides centralized authentication token resolution with fallback support
for multiple environment variables, and SDK environment variable passthrough
for custom API endpoints.
"""

import json
import os
import platform
import subprocess

# Priority order for auth token resolution
# NOTE: Azure Foundry API keys are supported for enterprise Azure deployments.
# For standard Claude Code usage, OAuth tokens are preferred to prevent
# silent billing to user's API credits when OAuth fails.
AUTH_TOKEN_ENV_VARS = [
    "CLAUDE_CODE_OAUTH_TOKEN",  # OAuth token from Claude Code CLI
    "ANTHROPIC_FOUNDRY_API_KEY",  # Azure Foundry API key (enterprise)
    "ANTHROPIC_AUTH_TOKEN",  # CCR/proxy token (for enterprise setups)
]

# NOTE: SDK environment variables are now handled in get_sdk_env_vars()
# based on the authentication mode (Foundry vs Standard) to prevent
# the "baseURL and resource are mutually exclusive" error.
#
# Environment variables to pass through to SDK subprocess
# NOTE: ANTHROPIC_API_KEY is intentionally excluded to prevent silent API billing
SDK_ENV_VARS = [
    # API endpoint configuration
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_AUTH_TOKEN",
    # Model overrides (from API Profile custom model mappings)
    "ANTHROPIC_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    # SDK behavior configuration
    "NO_PROXY",
    "DISABLE_TELEMETRY",
    "DISABLE_COST_WARNINGS",
    "API_TIMEOUT_MS",
]


def get_token_from_keychain() -> str | None:
    """
    Get authentication token from system credential store.

    Reads Claude Code credentials from:
    - macOS: Keychain
    - Windows: Credential Manager
    - Linux: Not yet supported (use env var)

    Returns:
        Token string if found, None otherwise
    """
    system = platform.system()

    if system == "Darwin":
        return _get_token_from_macos_keychain()
    elif system == "Windows":
        return _get_token_from_windows_credential_files()
    else:
        # Linux: secret-service not yet implemented
        return None


def _get_token_from_macos_keychain() -> str | None:
    """Get token from macOS Keychain."""
    try:
        result = subprocess.run(
            [
                "/usr/bin/security",
                "find-generic-password",
                "-s",
                "Claude Code-credentials",
                "-w",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return None

        credentials_json = result.stdout.strip()
        if not credentials_json:
            return None

        data = json.loads(credentials_json)
        token = data.get("claudeAiOauth", {}).get("accessToken")

        if not token:
            return None

        # Validate token format (Claude OAuth tokens start with sk-ant-oat01-)
        if not token.startswith("sk-ant-oat01-"):
            return None

        return token

    except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError, Exception):
        return None


def _get_token_from_windows_credential_files() -> str | None:
    """Get token from Windows credential files.

    Claude Code on Windows stores credentials in ~/.claude/.credentials.json
    """
    try:
        # Claude Code stores credentials in ~/.claude/.credentials.json
        cred_paths = [
            os.path.expandvars(r"%USERPROFILE%\.claude\.credentials.json"),
            os.path.expandvars(r"%USERPROFILE%\.claude\credentials.json"),
            os.path.expandvars(r"%LOCALAPPDATA%\Claude\credentials.json"),
            os.path.expandvars(r"%APPDATA%\Claude\credentials.json"),
        ]

        for cred_path in cred_paths:
            if os.path.exists(cred_path):
                with open(cred_path, encoding="utf-8") as f:
                    data = json.load(f)
                    token = data.get("claudeAiOauth", {}).get("accessToken")
                    if token and token.startswith("sk-ant-oat01-"):
                        return token

        return None

    except (json.JSONDecodeError, KeyError, FileNotFoundError, Exception):
        return None


def get_auth_token() -> str | None:
    """
    Get authentication token from environment variables or system credential store.

    Checks multiple sources in priority order:
    1. CLAUDE_CODE_OAUTH_TOKEN (env var)
    2. ANTHROPIC_AUTH_TOKEN (CCR/proxy env var for enterprise setups)
    3. System credential store (macOS Keychain, Windows Credential Manager)

    NOTE: ANTHROPIC_API_KEY is intentionally NOT supported to prevent
    silent billing to user's API credits when OAuth is misconfigured.

    Returns:
        Token string if found, None otherwise
    """
    # First check environment variables
    for var in AUTH_TOKEN_ENV_VARS:
        token = os.environ.get(var)
        if token:
            return token

    # Fallback to system credential store
    return get_token_from_keychain()


def get_auth_token_source() -> str | None:
    """Get the name of the source that provided the auth token."""
    # Check environment variables first
    for var in AUTH_TOKEN_ENV_VARS:
        if os.environ.get(var):
            return var

    # Check if token came from system credential store
    if get_token_from_keychain():
        system = platform.system()
        if system == "Darwin":
            return "macOS Keychain"
        elif system == "Windows":
            return "Windows Credential Files"
        else:
            return "System Credential Store"

    return None


def require_auth_token() -> str:
    """
    Get authentication token or raise ValueError.

    Raises:
        ValueError: If no auth token is found in any supported source
    """
    token = get_auth_token()
    if not token:
        error_msg = (
            "No OAuth token found.\n\n"
            "Auto Claude requires Claude Code OAuth authentication.\n"
            "Direct API keys (ANTHROPIC_API_KEY) are not supported.\n\n"
        )
        # Provide platform-specific guidance
        system = platform.system()
        if system == "Darwin":
            error_msg += (
                "To authenticate:\n"
                "  1. Run: claude setup-token\n"
                "  2. The token will be saved to macOS Keychain automatically\n\n"
                "Or set CLAUDE_CODE_OAUTH_TOKEN in your .env file."
            )
        elif system == "Windows":
            error_msg += (
                "To authenticate:\n"
                "  1. Run: claude setup-token\n"
                "  2. The token should be saved to Windows Credential Manager\n\n"
                "If auto-detection fails, set CLAUDE_CODE_OAUTH_TOKEN in your .env file.\n"
                "Check: %LOCALAPPDATA%\\Claude\\credentials.json"
            )
        else:
            error_msg += (
                "To authenticate:\n"
                "  1. Run: claude setup-token\n"
                "  2. Set CLAUDE_CODE_OAUTH_TOKEN in your .env file"
            )
        raise ValueError(error_msg)
    return token


def is_foundry_mode() -> bool:
    """
    Check if Azure Foundry authentication mode is enabled.

    Returns:
        True if CLAUDE_CODE_USE_FOUNDRY is set to '1' or 'true'
    """
    foundry = os.environ.get("CLAUDE_CODE_USE_FOUNDRY", "")
    return foundry in ("1", "true", "True")


def cleanup_conflicting_env_vars() -> None:
    """
    Remove conflicting environment variables based on authentication mode.

    The Claude Agent SDK raises "baseURL and resource are mutually exclusive" when:
    1. Both ANTHROPIC_BASE_URL and ANTHROPIC_FOUNDRY_RESOURCE are set
    2. Both ANTHROPIC_FOUNDRY_BASE_URL and ANTHROPIC_FOUNDRY_RESOURCE are set

    Per Azure Foundry docs, you should use EITHER:
    - ANTHROPIC_FOUNDRY_RESOURCE (preferred - Azure generates the URL)
    - ANTHROPIC_FOUNDRY_BASE_URL (alternative - you specify the full URL)

    This function should be called AFTER load_dotenv() to clean up conflicts.
    """
    if is_foundry_mode():
        # In Foundry mode, remove ANTHROPIC_BASE_URL to prevent conflict
        if "ANTHROPIC_BASE_URL" in os.environ:
            del os.environ["ANTHROPIC_BASE_URL"]

        # Also handle Foundry-internal conflict:
        # ANTHROPIC_FOUNDRY_BASE_URL and ANTHROPIC_FOUNDRY_RESOURCE are mutually exclusive
        # Prefer RESOURCE (simpler) over BASE_URL (explicit) if both are set
        has_resource = bool(os.environ.get("ANTHROPIC_FOUNDRY_RESOURCE"))
        has_base_url = bool(os.environ.get("ANTHROPIC_FOUNDRY_BASE_URL"))

        if has_resource and has_base_url:
            # Remove BASE_URL, keep RESOURCE (it's the recommended option)
            del os.environ["ANTHROPIC_FOUNDRY_BASE_URL"]

        # CRITICAL: If Foundry mode is enabled but neither RESOURCE nor BASE_URL is set,
        # disable Foundry mode to prevent the error:
        # "Must provide one of the `baseURL` or `resource` arguments"
        if not has_resource and not has_base_url:
            # Disable Foundry mode if not properly configured
            if "CLAUDE_CODE_USE_FOUNDRY" in os.environ:
                del os.environ["CLAUDE_CODE_USE_FOUNDRY"]
    else:
        # In standard mode, remove Foundry-specific vars
        foundry_vars = [
            "CLAUDE_CODE_USE_FOUNDRY",
            "ANTHROPIC_FOUNDRY_API_KEY",
            "ANTHROPIC_FOUNDRY_BASE_URL",
            "ANTHROPIC_FOUNDRY_RESOURCE",
        ]
        for var in foundry_vars:
            if var in os.environ:
                del os.environ[var]


def get_sdk_env_vars() -> dict[str, str]:
    """
    Get environment variables to pass to SDK.

    Collects relevant env vars based on the authentication mode.
    IMPORTANT: baseURL (ANTHROPIC_BASE_URL) and resource (ANTHROPIC_FOUNDRY_RESOURCE)
    are mutually exclusive in the Claude Agent SDK. This function ensures only
    the correct set of vars is passed based on the selected mode.

    When CLAUDE_CODE_USE_FOUNDRY=1:
      - Uses ANTHROPIC_FOUNDRY_* vars (Azure Foundry mode)
      - Excludes ANTHROPIC_BASE_URL to avoid conflict

    When CLAUDE_CODE_USE_FOUNDRY is not set:
      - Uses ANTHROPIC_BASE_URL if set
      - Excludes Foundry-specific vars

    Returns:
        Dict of env var name -> value for non-empty vars
    """
    env = {}

    # Determine which mode we're in
    foundry_mode = is_foundry_mode()

    # Define which vars to include based on mode
    if foundry_mode:
        # Azure Foundry mode - use Foundry vars, exclude ANTHROPIC_BASE_URL
        # NOTE: ANTHROPIC_FOUNDRY_BASE_URL and ANTHROPIC_FOUNDRY_RESOURCE are
        # mutually exclusive. Only include one (prefer RESOURCE if both exist).
        has_resource = bool(os.environ.get("ANTHROPIC_FOUNDRY_RESOURCE"))
        has_base_url = bool(os.environ.get("ANTHROPIC_FOUNDRY_BASE_URL"))

        allowed_vars = [
            "ANTHROPIC_AUTH_TOKEN",
            "CLAUDE_CODE_USE_FOUNDRY",
            "ANTHROPIC_FOUNDRY_API_KEY",
            "ANTHROPIC_DEFAULT_SONNET_MODEL",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL",
            "ANTHROPIC_DEFAULT_OPUS_MODEL",
            "NO_PROXY",
            "DISABLE_TELEMETRY",
            "DISABLE_COST_WARNINGS",
            "API_TIMEOUT_MS",
        ]

        # Add ONLY ONE of these (they are mutually exclusive)
        if has_resource:
            allowed_vars.append("ANTHROPIC_FOUNDRY_RESOURCE")
        elif has_base_url:
            allowed_vars.append("ANTHROPIC_FOUNDRY_BASE_URL")
    else:
        # Standard mode - use ANTHROPIC_BASE_URL, exclude Foundry vars
        allowed_vars = [
            "ANTHROPIC_BASE_URL",
            "ANTHROPIC_AUTH_TOKEN",
            "ANTHROPIC_DEFAULT_SONNET_MODEL",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL",
            "ANTHROPIC_DEFAULT_OPUS_MODEL",
            "NO_PROXY",
            "DISABLE_TELEMETRY",
            "DISABLE_COST_WARNINGS",
            "API_TIMEOUT_MS",
        ]

    for var in allowed_vars:
        value = os.environ.get(var)
        if value:
            env[var] = value

    return env


def ensure_claude_code_oauth_token() -> None:
    """
    Ensure CLAUDE_CODE_OAUTH_TOKEN is set (for SDK compatibility).

    If not set but other auth tokens are available, copies the value
    to CLAUDE_CODE_OAUTH_TOKEN so the underlying SDK can use it.
    """
    if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        return

    token = get_auth_token()
    if token:
        os.environ["CLAUDE_CODE_OAUTH_TOKEN"] = token
