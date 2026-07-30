class SEOOSError(Exception):
    """Base exception for all SEO OS errors."""


class ProjectNotFoundError(SEOOSError):
    """Raised when a project directory does not exist."""


class ProjectConfigError(SEOOSError):
    """Raised when project.yaml is missing, invalid, or fails validation."""


class SecretNotFoundError(SEOOSError):
    """Raised when a required environment variable secret is not set."""


class IntegrationError(SEOOSError):
    """Raised when an external API call fails."""


class SkillError(SEOOSError):
    """Raised when a skill cannot be loaded or executed."""


class AgentError(SEOOSError):
    """Raised when an agent encounters an unrecoverable error."""
