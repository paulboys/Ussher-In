"""Translation adapters for the Ussher pipeline.

The primary adapter shells out to the Claude Code CLI (``claude -p``)
rather than calling the Anthropic API directly. This keeps automation
aligned with the CLI permission model already established in
``.claude/settings.local.json`` and the existing
``scripts/run_agent_loop.ps1`` invocation pattern.

All external interactions are routed through an injectable
``CommandRunner`` callable so unit tests can supply deterministic
fakes (mirroring the ``request_fn`` seam used by the Gemini OCR
adapter).
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from provider_config import ProviderConfig


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class TranslationError(Exception):
    """Base class for translation adapter errors."""

    category: str = "unknown"


class CLIUnavailableError(TranslationError):
    category = "cli_not_found"


class TranslationTimeoutError(TranslationError):
    category = "timeout"


class MalformedOutputError(TranslationError):
    category = "malformed_json"


class TranslationPermissionError(TranslationError):
    category = "permission_denied"


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------


@dataclass
class CommandResult:
    """Captured outcome of a single Claude CLI invocation."""

    stdout: str
    stderr: str = ""
    returncode: int = 0


@dataclass
class TranslationUnit:
    """One translated body line or footnote."""

    unit_id: str
    english: str
    notes: str = ""
    uncertain: bool = False


@dataclass
class TranslationResult:
    """Structured outcome of a single translation request.

    ``translations`` is keyed by ``line_id`` / ``footnote_id`` so the
    runner can persist append-only history without ambiguity.
    """

    translations: dict[str, TranslationUnit]
    raw_response: str
    usage_tokens: dict[str, int] | None = None
    errors: list[str] = field(default_factory=list)
    prompt: str = ""


# ---------------------------------------------------------------------------
# Command runner seam
# ---------------------------------------------------------------------------


CommandRunner = Callable[[Sequence[str], str, float], CommandResult]


def _default_command_runner(
    argv: Sequence[str],
    stdin_text: str,
    timeout_seconds: float,
) -> CommandResult:
    """Default runner that invokes the Claude CLI via subprocess."""

    try:
        completed = subprocess.run(
            list(argv),
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        raise CLIUnavailableError(
            f"Claude CLI executable not found on PATH: {argv[0]!r}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise TranslationTimeoutError(
            f"Claude CLI timed out after {timeout_seconds}s"
        ) from exc
    return CommandResult(
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        returncode=completed.returncode,
    )


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------


_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


def _strip_code_fence(text: str) -> str:
    match = _FENCE_RE.match(text or "")
    return match.group(1) if match else text


def _extract_json_object(text: str) -> dict[str, Any]:
    """Return the first balanced JSON object found in *text*.

    Tolerates leading prose or a single fenced ```json block, but the
    extracted object MUST parse as valid JSON or this raises
    ``MalformedOutputError``.
    """

    candidate = _strip_code_fence(text or "").strip()
    if not candidate:
        raise MalformedOutputError("Claude CLI returned empty output")

    # Fast path: whole payload is JSON.
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Scan for a balanced top-level object.
    start = candidate.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escape = False
        for idx in range(start, len(candidate)):
            ch = candidate[idx]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    blob = candidate[start : idx + 1]
                    try:
                        parsed = json.loads(blob)
                    except json.JSONDecodeError:
                        break
                    if isinstance(parsed, dict):
                        return parsed
                    break
        start = candidate.find("{", start + 1)

    raise MalformedOutputError(
        "Claude CLI output did not contain a valid JSON object"
    )


def parse_translation_payload(
    raw: str,
    *,
    expected_unit_ids: Sequence[str] = (),
) -> tuple[dict[str, TranslationUnit], list[str]]:
    """Parse the strict translation contract output.

    Returns the keyed ``TranslationUnit`` map and a list of
    non-fatal warnings (missing IDs, unexpected IDs).
    """

    payload = _extract_json_object(raw)
    translations_raw = payload.get("translations")
    if not isinstance(translations_raw, dict):
        raise MalformedOutputError(
            "JSON payload missing 'translations' object"
        )

    units: dict[str, TranslationUnit] = {}
    warnings: list[str] = []

    for unit_id, entry in translations_raw.items():
        if not isinstance(entry, dict):
            warnings.append(f"non-object entry for {unit_id!r}; skipped")
            continue
        english = entry.get("english")
        if not isinstance(english, str):
            warnings.append(f"missing or non-string 'english' for {unit_id!r}")
            english = ""
        notes = entry.get("notes", "")
        if not isinstance(notes, str):
            notes = ""
        uncertain = bool(entry.get("uncertain", False))
        units[str(unit_id)] = TranslationUnit(
            unit_id=str(unit_id),
            english=english,
            notes=notes,
            uncertain=uncertain,
        )

    if expected_unit_ids:
        expected_set = set(expected_unit_ids)
        returned_set = set(units.keys())
        missing = sorted(expected_set - returned_set)
        unexpected = sorted(returned_set - expected_set)
        if missing:
            warnings.append(
                "missing translations for unit_ids: " + ", ".join(missing)
            )
        if unexpected:
            warnings.append(
                "unexpected unit_ids in response: " + ", ".join(unexpected)
            )

    return units, warnings


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class AnthropicTranslationAdapter:
    """Translation adapter backed by the Claude Code CLI.

    The adapter sends a single prompt and parses the JSON response into
    a :class:`TranslationResult`. It is deliberately stateless apart
    from configuration: callers pass already-built prompts (see
    :mod:`translation_prompts`).
    """

    def __init__(
        self,
        provider: ProviderConfig,
        *,
        command_runner: CommandRunner | None = None,
        cli_path: str = "claude",
        permission_mode: str = "dangerously-skip-permissions",
    ) -> None:
        if provider.name != "anthropic":
            raise ValueError(
                "AnthropicTranslationAdapter expects provider.name='anthropic', "
                f"got {provider.name!r}"
            )
        if not provider.supports_translation:
            raise ValueError(
                "Provider is not configured for translation "
                "(supports_translation=False)"
            )
        self.provider = provider
        self._runner: CommandRunner = command_runner or _default_command_runner
        self._cli_path = cli_path
        self._permission_mode = permission_mode

    # -- introspection -----------------------------------------------------

    def is_ready(self) -> bool:
        """The CLI handles its own authentication; readiness is taken
        as ``provider.supports_translation`` plus a non-empty CLI path.
        Live CLI presence is tested at call time via the runner.
        """

        return bool(self._cli_path) and self.provider.supports_translation

    # -- core call ---------------------------------------------------------

    def _build_argv(self, prompt: str) -> list[str]:
        argv = [self._cli_path, "-p", prompt]
        if self._permission_mode == "dangerously-skip-permissions":
            argv.append("--dangerously-skip-permissions")
        return argv

    def translate_units(
        self,
        prompt: str,
        *,
        expected_unit_ids: Sequence[str] = (),
    ) -> TranslationResult:
        """Send *prompt* to Claude CLI and return parsed translations.

        Retries up to ``provider.max_retries`` times on
        ``MalformedOutputError`` only; permission and timeout errors
        propagate immediately.
        """

        attempts = max(1, self.provider.max_retries + 1)
        last_error: Exception | None = None
        last_raw = ""

        for _ in range(attempts):
            argv = self._build_argv(prompt)
            result = self._runner(argv, "", float(self.provider.timeout_seconds))
            last_raw = result.stdout

            if result.returncode != 0:
                stderr = result.stderr or ""
                lowered = stderr.lower()
                if "permission" in lowered or "not allowed" in lowered:
                    raise TranslationPermissionError(stderr.strip())
                # treat other non-zero exits as malformed; retry
                last_error = MalformedOutputError(
                    f"Claude CLI exited with code {result.returncode}: "
                    f"{stderr.strip()[:200]}"
                )
                continue

            try:
                units, warnings = parse_translation_payload(
                    result.stdout,
                    expected_unit_ids=expected_unit_ids,
                )
            except MalformedOutputError as exc:
                last_error = exc
                continue

            return TranslationResult(
                translations=units,
                raw_response=result.stdout,
                usage_tokens=_extract_usage_tokens(result.stderr),
                errors=warnings,
                prompt=prompt,
            )

        assert last_error is not None
        raise last_error

    # -- single-line compatibility shim -----------------------------------

    def translate_text(
        self,
        latin_text: str,
        *,
        unit_id: str = "unit_0",
        prompt_builder: Callable[[str, str], str] | None = None,
    ) -> str:
        """Translate a single free-form Latin string to English.

        Provided so legacy callers that just want plain text continue
        to work; production runs should use ``translate_units`` with a
        properly-built page prompt.
        """

        if prompt_builder is None:
            prompt = (
                "Translate the following 17th-century Latin into modern "
                "English. Return JSON shaped exactly as "
                '{"translations": {"' + unit_id + '": {"english": "...", '
                '"notes": "", "uncertain": false}}} and nothing else.\n\n'
                f"{unit_id}: {latin_text}\n"
            )
        else:
            prompt = prompt_builder(unit_id, latin_text)

        result = self.translate_units(prompt, expected_unit_ids=[unit_id])
        unit = result.translations.get(unit_id)
        if unit is None:
            raise MalformedOutputError(
                f"Translation result did not contain unit_id {unit_id!r}"
            )
        return unit.english


# ---------------------------------------------------------------------------
# Optional usage extraction
# ---------------------------------------------------------------------------


_USAGE_RE = re.compile(
    r"(input_tokens|output_tokens|total_tokens)\s*[=:]\s*(\d+)",
    re.IGNORECASE,
)


def _extract_usage_tokens(stderr: str) -> dict[str, int] | None:
    """Best-effort scan of CLI stderr for usage telemetry.

    The Claude CLI's stderr format is not stable; if no recognized
    fields are present this returns ``None`` so artifacts can record
    an explicit nullable for future direct-API migration.
    """

    if not stderr:
        return None
    matches = _USAGE_RE.findall(stderr)
    if not matches:
        return None
    return {key.lower(): int(value) for key, value in matches}


__all__ = [
    "AnthropicTranslationAdapter",
    "CLIUnavailableError",
    "CommandResult",
    "CommandRunner",
    "MalformedOutputError",
    "TranslationError",
    "TranslationPermissionError",
    "TranslationResult",
    "TranslationTimeoutError",
    "TranslationUnit",
    "parse_translation_payload",
]
