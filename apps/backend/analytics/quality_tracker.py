# apps/backend/analytics/quality_tracker.py
"""
Quality Tracker - Code quality metrics for specs.

Analyzes code quality using available linters and type checkers,
calculates quality grades, and stores results in the analytics database.
"""

import asyncio
import json
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

from .storage import get_analytics_storage, AnalyticsStorage

logger = logging.getLogger(__name__)


@dataclass
class LintResult:
    """Result from running a linter."""
    linter: str
    errors: int = 0
    warnings: int = 0
    raw_output: str = ""
    success: bool = True


@dataclass
class TypeCheckResult:
    """Result from running a type checker."""
    checker: str
    errors: int = 0
    raw_output: str = ""
    success: bool = True


@dataclass
class QualityMetrics:
    """Quality metrics for a spec."""
    spec_id: str
    lint_errors: int = 0
    lint_warnings: int = 0
    type_errors: int = 0
    test_coverage_percent: Optional[float] = None
    complexity_score: Optional[float] = None
    quality_grade: str = "F"  # A, B, C, D, F
    analyzed_at: datetime = field(default_factory=datetime.utcnow)
    linter_used: Optional[str] = None
    type_checker_used: Optional[str] = None
    raw_results: Dict[str, Any] = field(default_factory=dict)


# Linter configuration: config files -> linter name
LINTER_CONFIG_FILES = {
    # ESLint (JavaScript/TypeScript)
    "eslint.config.js": "eslint",
    "eslint.config.mjs": "eslint",
    "eslint.config.cjs": "eslint",
    ".eslintrc": "eslint",
    ".eslintrc.js": "eslint",
    ".eslintrc.cjs": "eslint",
    ".eslintrc.json": "eslint",
    ".eslintrc.yml": "eslint",
    ".eslintrc.yaml": "eslint",
    # Ruff (Python - fast)
    "ruff.toml": "ruff",
    ".ruff.toml": "ruff",
    # Pylint (Python)
    ".pylintrc": "pylint",
    "pylintrc": "pylint",
    # Flake8 (Python)
    ".flake8": "flake8",
    # Biome (JavaScript/TypeScript)
    "biome.json": "biome",
    "biome.jsonc": "biome",
    # Prettier (formatting - JavaScript/TypeScript)
    ".prettierrc": "prettier",
    ".prettierrc.json": "prettier",
    ".prettierrc.js": "prettier",
    "prettier.config.js": "prettier",
    # Stylelint (CSS)
    ".stylelintrc": "stylelint",
    ".stylelintrc.json": "stylelint",
    "stylelint.config.js": "stylelint",
    # RuboCop (Ruby)
    ".rubocop.yml": "rubocop",
    # GolangCI-Lint (Go)
    ".golangci.yml": "golangci-lint",
    ".golangci.yaml": "golangci-lint",
    # Clippy config via Cargo.toml is standard for Rust
    # SwiftLint
    ".swiftlint.yml": "swiftlint",
}

# Type checker configuration: config files -> checker name
TYPE_CHECKER_CONFIG_FILES = {
    # TypeScript
    "tsconfig.json": "tsc",
    # Python mypy
    "mypy.ini": "mypy",
    ".mypy.ini": "mypy",
    # Python pyright
    "pyrightconfig.json": "pyright",
}


class QualityTracker:
    """
    Tracks code quality metrics for specs.

    Detects and runs available linters and type checkers,
    calculates quality grades, and stores results.
    """

    def __init__(
        self,
        project_dir: Path,
        spec_id: str,
        storage: Optional[AnalyticsStorage] = None
    ):
        """
        Initialize quality tracker.

        Args:
            project_dir: Root directory of the project
            spec_id: Spec identifier
            storage: Optional analytics storage instance
        """
        self.project_dir = Path(project_dir).resolve()
        self.spec_id = spec_id
        self.storage = storage or get_analytics_storage()

    def _file_exists(self, *paths: str) -> bool:
        """Check if any of the given files exist."""
        for p in paths:
            if "*" in p:
                if list(self.project_dir.glob(p)):
                    return True
            else:
                if (self.project_dir / p).exists():
                    return True
        return False

    def _read_json(self, filename: str) -> Optional[dict]:
        """Read a JSON file from project root."""
        try:
            with open(self.project_dir / filename) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    def _detect_linter(self) -> Optional[str]:
        """
        Detect available linter for the project.

        Returns:
            Linter name or None if no linter detected
        """
        # Check for explicit config files first
        for config_file, linter in LINTER_CONFIG_FILES.items():
            if self._file_exists(config_file):
                logger.debug(f"Detected linter {linter} from config file {config_file}")
                return linter

        # Check pyproject.toml for Python linters
        if self._file_exists("pyproject.toml"):
            try:
                import sys
                if sys.version_info >= (3, 11):
                    import tomllib
                else:
                    try:
                        import tomli as tomllib
                    except ImportError:
                        tomllib = None

                if tomllib:
                    with open(self.project_dir / "pyproject.toml", "rb") as f:
                        toml_data = tomllib.load(f)
                        tool = toml_data.get("tool", {})
                        if "ruff" in tool:
                            return "ruff"
                        if "pylint" in tool:
                            return "pylint"
                        if "flake8" in tool:
                            return "flake8"
            except Exception as e:
                logger.debug(f"Error reading pyproject.toml: {e}")

        # Check package.json for JavaScript/TypeScript linters
        package_json = self._read_json("package.json")
        if package_json:
            deps = {}
            deps.update(package_json.get("dependencies", {}))
            deps.update(package_json.get("devDependencies", {}))

            if "eslint" in deps:
                return "eslint"
            if "@biomejs/biome" in deps or "biome" in deps:
                return "biome"

        # Detect by project type as fallback
        if self._file_exists("*.py", "**/*.py", "pyproject.toml", "requirements.txt"):
            # Python project - check if ruff/pylint/flake8 is available
            for linter in ["ruff", "pylint", "flake8"]:
                if self._is_command_available(linter):
                    return linter

        if self._file_exists("*.js", "*.ts", "**/*.js", "**/*.ts", "package.json"):
            # JavaScript/TypeScript project
            if self._is_command_available("npx"):
                # Check if eslint is available via npx
                return "eslint"

        if self._file_exists("Cargo.toml"):
            return "clippy"

        if self._file_exists("go.mod"):
            return "golangci-lint"

        if self._file_exists("Gemfile", "*.rb"):
            return "rubocop"

        if self._file_exists("Package.swift", "*.swift"):
            return "swiftlint"

        return None

    def _detect_type_checker(self) -> Optional[str]:
        """
        Detect available type checker for the project.

        Returns:
            Type checker name or None if no checker detected
        """
        # Check for explicit config files
        for config_file, checker in TYPE_CHECKER_CONFIG_FILES.items():
            if self._file_exists(config_file):
                logger.debug(f"Detected type checker {checker} from config file {config_file}")
                return checker

        # Check pyproject.toml for mypy/pyright
        if self._file_exists("pyproject.toml"):
            try:
                import sys
                if sys.version_info >= (3, 11):
                    import tomllib
                else:
                    try:
                        import tomli as tomllib
                    except ImportError:
                        tomllib = None

                if tomllib:
                    with open(self.project_dir / "pyproject.toml", "rb") as f:
                        toml_data = tomllib.load(f)
                        tool = toml_data.get("tool", {})
                        if "mypy" in tool:
                            return "mypy"
                        if "pyright" in tool:
                            return "pyright"
            except Exception as e:
                logger.debug(f"Error reading pyproject.toml: {e}")

        # TypeScript projects have type checking built-in
        if self._file_exists("tsconfig.json"):
            return "tsc"

        # Rust has built-in type checking via cargo check
        if self._file_exists("Cargo.toml"):
            return "cargo_check"

        # Go has built-in type checking
        if self._file_exists("go.mod"):
            return "go_vet"

        return None

    def _is_command_available(self, command: str) -> bool:
        """Check if a command is available in the system."""
        try:
            result = subprocess.run(
                ["which", command],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def _run_linter(self, linter: str) -> LintResult:
        """
        Run linter and collect results.

        Args:
            linter: Name of the linter to run

        Returns:
            LintResult with error and warning counts
        """
        result = LintResult(linter=linter)

        try:
            if linter == "eslint":
                result = self._run_eslint()
            elif linter == "ruff":
                result = self._run_ruff()
            elif linter == "pylint":
                result = self._run_pylint()
            elif linter == "flake8":
                result = self._run_flake8()
            elif linter == "biome":
                result = self._run_biome()
            elif linter == "clippy":
                result = self._run_clippy()
            elif linter == "golangci-lint":
                result = self._run_golangci_lint()
            elif linter == "rubocop":
                result = self._run_rubocop()
            elif linter == "swiftlint":
                result = self._run_swiftlint()
            else:
                logger.warning(f"Unknown linter: {linter}")
                result.success = False

        except subprocess.TimeoutExpired:
            logger.warning(f"Linter {linter} timed out")
            result.success = False
        except Exception as e:
            logger.warning(f"Error running linter {linter}: {e}")
            result.success = False

        return result

    def _run_eslint(self) -> LintResult:
        """Run ESLint and parse results."""
        result = LintResult(linter="eslint")

        # Try npx eslint with JSON output
        cmd = ["npx", "eslint", ".", "--format", "json", "--max-warnings", "0"]

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            result.raw_output = proc.stdout

            # Parse JSON output
            if proc.stdout:
                try:
                    data = json.loads(proc.stdout)
                    for file_result in data:
                        for msg in file_result.get("messages", []):
                            severity = msg.get("severity", 0)
                            if severity == 2:  # Error
                                result.errors += 1
                            elif severity == 1:  # Warning
                                result.warnings += 1
                except json.JSONDecodeError:
                    # Fallback: count lines in stderr
                    result.errors = proc.stderr.count("error")
                    result.warnings = proc.stderr.count("warning")

        except subprocess.TimeoutExpired:
            result.success = False
            logger.warning("ESLint timed out")

        return result

    def _run_ruff(self) -> LintResult:
        """Run Ruff and parse results."""
        result = LintResult(linter="ruff")

        cmd = ["ruff", "check", ".", "--output-format", "json"]

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            result.raw_output = proc.stdout

            # Parse JSON output
            if proc.stdout:
                try:
                    data = json.loads(proc.stdout)
                    # Ruff outputs a list of violations
                    for violation in data:
                        # Ruff doesn't distinguish error/warning by default
                        # E/F codes are errors, W codes are warnings
                        code = violation.get("code", "")
                        if code.startswith("W"):
                            result.warnings += 1
                        else:
                            result.errors += 1
                except json.JSONDecodeError:
                    # Count lines as fallback
                    result.errors = len(proc.stdout.strip().split("\n")) if proc.stdout.strip() else 0

        except FileNotFoundError:
            result.success = False
            logger.debug("Ruff not found")

        return result

    def _run_pylint(self) -> LintResult:
        """Run Pylint and parse results."""
        result = LintResult(linter="pylint")

        cmd = ["pylint", ".", "--output-format", "json", "--recursive", "y"]

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=180
            )
            result.raw_output = proc.stdout

            # Parse JSON output
            if proc.stdout:
                try:
                    data = json.loads(proc.stdout)
                    for msg in data:
                        msg_type = msg.get("type", "")
                        if msg_type in ["error", "fatal"]:
                            result.errors += 1
                        elif msg_type in ["warning", "convention", "refactor"]:
                            result.warnings += 1
                except json.JSONDecodeError:
                    pass

        except FileNotFoundError:
            result.success = False
            logger.debug("Pylint not found")

        return result

    def _run_flake8(self) -> LintResult:
        """Run Flake8 and parse results."""
        result = LintResult(linter="flake8")

        cmd = ["flake8", ".", "--format", "json"]

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            result.raw_output = proc.stdout

            # Parse JSON output (if available) or count lines
            if proc.stdout:
                try:
                    # flake8-json format
                    data = json.loads(proc.stdout)
                    for file_path, violations in data.items():
                        for v in violations:
                            code = v.get("code", "")
                            if code.startswith("E") or code.startswith("F"):
                                result.errors += 1
                            else:
                                result.warnings += 1
                except json.JSONDecodeError:
                    # Default format: count lines
                    lines = proc.stdout.strip().split("\n")
                    result.errors = len([l for l in lines if l.strip()])

        except FileNotFoundError:
            result.success = False
            logger.debug("Flake8 not found")

        return result

    def _run_biome(self) -> LintResult:
        """Run Biome and parse results."""
        result = LintResult(linter="biome")

        cmd = ["npx", "@biomejs/biome", "lint", ".", "--reporter", "json"]

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            result.raw_output = proc.stdout

            if proc.stdout:
                try:
                    data = json.loads(proc.stdout)
                    diagnostics = data.get("diagnostics", [])
                    for diag in diagnostics:
                        severity = diag.get("severity", "error")
                        if severity == "error":
                            result.errors += 1
                        else:
                            result.warnings += 1
                except json.JSONDecodeError:
                    pass

        except FileNotFoundError:
            result.success = False

        return result

    def _run_clippy(self) -> LintResult:
        """Run Cargo Clippy and parse results."""
        result = LintResult(linter="clippy")

        cmd = ["cargo", "clippy", "--message-format", "json", "--", "-W", "clippy::all"]

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            result.raw_output = proc.stdout

            # Parse JSON Lines output
            for line in proc.stdout.split("\n"):
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                    if msg.get("reason") == "compiler-message":
                        level = msg.get("message", {}).get("level", "")
                        if level == "error":
                            result.errors += 1
                        elif level == "warning":
                            result.warnings += 1
                except json.JSONDecodeError:
                    continue

        except FileNotFoundError:
            result.success = False

        return result

    def _run_golangci_lint(self) -> LintResult:
        """Run golangci-lint and parse results."""
        result = LintResult(linter="golangci-lint")

        cmd = ["golangci-lint", "run", "--out-format", "json"]

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            result.raw_output = proc.stdout

            if proc.stdout:
                try:
                    data = json.loads(proc.stdout)
                    issues = data.get("Issues", [])
                    for issue in issues:
                        severity = issue.get("Severity", "error")
                        if severity == "error":
                            result.errors += 1
                        else:
                            result.warnings += 1
                except json.JSONDecodeError:
                    pass

        except FileNotFoundError:
            result.success = False

        return result

    def _run_rubocop(self) -> LintResult:
        """Run RuboCop and parse results."""
        result = LintResult(linter="rubocop")

        cmd = ["rubocop", "--format", "json"]

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            result.raw_output = proc.stdout

            if proc.stdout:
                try:
                    data = json.loads(proc.stdout)
                    summary = data.get("summary", {})
                    result.errors = summary.get("offense_count", 0)
                    # RuboCop doesn't have separate warning count by default
                except json.JSONDecodeError:
                    pass

        except FileNotFoundError:
            result.success = False

        return result

    def _run_swiftlint(self) -> LintResult:
        """Run SwiftLint and parse results."""
        result = LintResult(linter="swiftlint")

        cmd = ["swiftlint", "lint", "--reporter", "json"]

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            result.raw_output = proc.stdout

            if proc.stdout:
                try:
                    data = json.loads(proc.stdout)
                    for violation in data:
                        severity = violation.get("severity", "Warning")
                        if severity == "Error":
                            result.errors += 1
                        else:
                            result.warnings += 1
                except json.JSONDecodeError:
                    pass

        except FileNotFoundError:
            result.success = False

        return result

    def _run_type_checker(self, checker: str) -> TypeCheckResult:
        """
        Run type checker and collect results.

        Args:
            checker: Name of the type checker to run

        Returns:
            TypeCheckResult with error count
        """
        result = TypeCheckResult(checker=checker)

        try:
            if checker == "tsc":
                result = self._run_tsc()
            elif checker == "mypy":
                result = self._run_mypy()
            elif checker == "pyright":
                result = self._run_pyright()
            elif checker == "cargo_check":
                result = self._run_cargo_check()
            elif checker == "go_vet":
                result = self._run_go_vet()
            else:
                logger.warning(f"Unknown type checker: {checker}")
                result.success = False

        except subprocess.TimeoutExpired:
            logger.warning(f"Type checker {checker} timed out")
            result.success = False
        except Exception as e:
            logger.warning(f"Error running type checker {checker}: {e}")
            result.success = False

        return result

    def _run_tsc(self) -> TypeCheckResult:
        """Run TypeScript compiler and parse results."""
        result = TypeCheckResult(checker="tsc")

        cmd = ["npx", "tsc", "--noEmit"]

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            result.raw_output = proc.stderr + proc.stdout

            # Count error lines (TypeScript errors start with file path)
            output = proc.stderr + proc.stdout
            # Each error line typically contains ": error TS"
            result.errors = output.count(": error TS")

        except FileNotFoundError:
            result.success = False

        return result

    def _run_mypy(self) -> TypeCheckResult:
        """Run mypy and parse results."""
        result = TypeCheckResult(checker="mypy")

        cmd = ["mypy", ".", "--show-error-codes"]

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=180
            )
            result.raw_output = proc.stdout

            # Count error lines
            for line in proc.stdout.split("\n"):
                if ": error:" in line:
                    result.errors += 1

        except FileNotFoundError:
            result.success = False

        return result

    def _run_pyright(self) -> TypeCheckResult:
        """Run Pyright and parse results."""
        result = TypeCheckResult(checker="pyright")

        cmd = ["pyright", "--outputjson"]

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=180
            )
            result.raw_output = proc.stdout

            if proc.stdout:
                try:
                    data = json.loads(proc.stdout)
                    summary = data.get("summary", {})
                    result.errors = summary.get("errorCount", 0)
                except json.JSONDecodeError:
                    pass

        except FileNotFoundError:
            result.success = False

        return result

    def _run_cargo_check(self) -> TypeCheckResult:
        """Run cargo check and parse results."""
        result = TypeCheckResult(checker="cargo_check")

        cmd = ["cargo", "check", "--message-format", "json"]

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            result.raw_output = proc.stdout

            # Parse JSON Lines output
            for line in proc.stdout.split("\n"):
                if not line.strip():
                    continue
                try:
                    msg = json.loads(line)
                    if msg.get("reason") == "compiler-message":
                        level = msg.get("message", {}).get("level", "")
                        if level == "error":
                            result.errors += 1
                except json.JSONDecodeError:
                    continue

        except FileNotFoundError:
            result.success = False

        return result

    def _run_go_vet(self) -> TypeCheckResult:
        """Run go vet and parse results."""
        result = TypeCheckResult(checker="go_vet")

        cmd = ["go", "vet", "./..."]

        try:
            proc = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            result.raw_output = proc.stderr

            # Count error lines in stderr
            if proc.stderr:
                result.errors = len([l for l in proc.stderr.strip().split("\n") if l.strip()])

        except FileNotFoundError:
            result.success = False

        return result

    def _calculate_grade(
        self,
        lint_result: Optional[LintResult],
        type_result: Optional[TypeCheckResult]
    ) -> str:
        """
        Calculate quality grade based on lint and type check results.

        Grade calculation:
        - A: 0 errors, < 5 warnings
        - B: 0 errors, < 10 warnings
        - C: 1-5 errors, any warnings
        - D: 6-10 errors
        - F: > 10 errors

        Args:
            lint_result: Result from linter
            type_result: Result from type checker

        Returns:
            Grade letter (A, B, C, D, F)
        """
        total_errors = 0
        total_warnings = 0

        if lint_result and lint_result.success:
            total_errors += lint_result.errors
            total_warnings += lint_result.warnings

        if type_result and type_result.success:
            total_errors += type_result.errors

        # Calculate grade
        if total_errors == 0 and total_warnings < 5:
            return "A"
        elif total_errors == 0 and total_warnings < 10:
            return "B"
        elif total_errors >= 1 and total_errors <= 5:
            return "C"
        elif total_errors >= 6 and total_errors <= 10:
            return "D"
        else:
            return "F"

    async def _store_metrics(self, metrics: QualityMetrics) -> None:
        """
        Store quality metrics in the database.

        Args:
            metrics: QualityMetrics to store
        """
        loop = asyncio.get_event_loop()

        def _store():
            conn = self.storage._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO spec_quality_metrics (
                    spec_id, lint_errors, lint_warnings, type_errors,
                    test_coverage_percent, complexity_score, quality_grade, analyzed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(spec_id) DO UPDATE SET
                    lint_errors = excluded.lint_errors,
                    lint_warnings = excluded.lint_warnings,
                    type_errors = excluded.type_errors,
                    test_coverage_percent = excluded.test_coverage_percent,
                    complexity_score = excluded.complexity_score,
                    quality_grade = excluded.quality_grade,
                    analyzed_at = excluded.analyzed_at
            """, (
                metrics.spec_id,
                metrics.lint_errors,
                metrics.lint_warnings,
                metrics.type_errors,
                metrics.test_coverage_percent,
                metrics.complexity_score,
                metrics.quality_grade,
                metrics.analyzed_at.isoformat()
            ))

            conn.commit()
            conn.close()

        await loop.run_in_executor(None, _store)

    async def analyze_quality(self) -> QualityMetrics:
        """
        Analyze code quality for the project.

        Detects available linter and type checker, runs them,
        calculates quality grade, and stores results.

        Returns:
            QualityMetrics with all results
        """
        logger.info(f"Analyzing code quality for spec {self.spec_id}")

        # Initialize metrics
        metrics = QualityMetrics(spec_id=self.spec_id)

        # Detect and run linter
        linter = self._detect_linter()
        lint_result = None
        if linter:
            logger.info(f"Running linter: {linter}")
            lint_result = self._run_linter(linter)
            metrics.lint_errors = lint_result.errors
            metrics.lint_warnings = lint_result.warnings
            metrics.linter_used = linter
            metrics.raw_results["lint"] = {
                "linter": linter,
                "errors": lint_result.errors,
                "warnings": lint_result.warnings,
                "success": lint_result.success
            }
        else:
            logger.info("No linter detected for project")

        # Detect and run type checker
        checker = self._detect_type_checker()
        type_result = None
        if checker:
            logger.info(f"Running type checker: {checker}")
            type_result = self._run_type_checker(checker)
            metrics.type_errors = type_result.errors
            metrics.type_checker_used = checker
            metrics.raw_results["type_check"] = {
                "checker": checker,
                "errors": type_result.errors,
                "success": type_result.success
            }
        else:
            logger.info("No type checker detected for project")

        # Calculate grade
        metrics.quality_grade = self._calculate_grade(lint_result, type_result)
        metrics.analyzed_at = datetime.utcnow()

        logger.info(
            f"Quality analysis complete: Grade={metrics.quality_grade}, "
            f"Lint Errors={metrics.lint_errors}, Warnings={metrics.lint_warnings}, "
            f"Type Errors={metrics.type_errors}"
        )

        # Store in database
        await self._store_metrics(metrics)

        return metrics

    async def get_quality_metrics(self) -> Optional[QualityMetrics]:
        """
        Get stored quality metrics for the spec.

        Returns:
            QualityMetrics if found, None otherwise
        """
        loop = asyncio.get_event_loop()

        def _get():
            conn = self.storage._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM spec_quality_metrics WHERE spec_id = ?
            """, (self.spec_id,))

            row = cursor.fetchone()
            conn.close()

            if row:
                return QualityMetrics(
                    spec_id=row["spec_id"],
                    lint_errors=row["lint_errors"],
                    lint_warnings=row["lint_warnings"],
                    type_errors=row["type_errors"],
                    test_coverage_percent=row["test_coverage_percent"],
                    complexity_score=row["complexity_score"],
                    quality_grade=row["quality_grade"],
                    analyzed_at=datetime.fromisoformat(row["analyzed_at"]) if row["analyzed_at"] else datetime.utcnow()
                )
            return None

        return await loop.run_in_executor(None, _get)


# Factory function
def create_quality_tracker(
    project_dir: Path,
    spec_id: str,
    db_path: Optional[str] = None
) -> QualityTracker:
    """
    Create a QualityTracker instance.

    Args:
        project_dir: Root directory of the project
        spec_id: Spec identifier
        db_path: Optional path to analytics database

    Returns:
        QualityTracker instance
    """
    storage = get_analytics_storage(db_path)
    return QualityTracker(project_dir, spec_id, storage)
