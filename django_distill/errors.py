class DistillError(Exception):
    """Base class for all Distill errors."""


class DistillWarning(RuntimeWarning):
    """Base class for all Distill warnings."""


class DistillPublishError(DistillError):
    """Raised when there is an error publishing a Distilled site."""


class DistillRenderError(DistillError):
    """Raised when there is an error rendering a Distilled site."""
