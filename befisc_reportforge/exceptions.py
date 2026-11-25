"""Exception hierarchy for befisc_reportforge."""

from __future__ import annotations


class ReportForgeError(Exception):
    """Base class for every error raised by the engine."""


class InputError(ReportForgeError):
    """The input could not be read or is not valid JSON."""


class ValidationError(ReportForgeError):
    """The JSON is readable but does not have the structure a template needs."""

    def __init__(self, message: str, problems: list[str] | None = None) -> None:
        self.problems = list(problems or [])
        if self.problems:
            message = message + ":\n  - " + "\n  - ".join(self.problems)
        super().__init__(message)


class AssetError(ReportForgeError):
    """A font, logo or other asset is missing or unusable."""


class TemplateError(ReportForgeError):
    """An unknown template was requested or a template is misconfigured."""


class RenderError(ReportForgeError):
    """The PDF could not be built or written."""
