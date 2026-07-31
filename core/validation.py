from dataclasses import dataclass, field

from core.models.project import ProjectConfig

_PLACEHOLDER_VALUES = {
    "website": "https://example.com",
    "business_name": "Your Business Name",
    "target_audience": "describe your target audience here",
}

_KNOWN_CMS = ("wordpress", "shopify", "nextjs", "static")


@dataclass
class ValidationReport:
    project: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0


def validate_config(project_name: str, config: ProjectConfig) -> ValidationReport:
    report = ValidationReport(project=project_name)

    for field_name, placeholder in _PLACEHOLDER_VALUES.items():
        if str(getattr(config, field_name, "")) == placeholder:
            report.warnings.append(f"'{field_name}' still has its placeholder value")

    if not config.seo_goals:
        report.warnings.append("'seo_goals' is empty")
    if not config.business_goals:
        report.warnings.append("'business_goals' is empty")
    if not config.competitors:
        report.warnings.append("'competitors' is empty")
    if config.cms not in _KNOWN_CMS:
        report.warnings.append(f"'cms' value '{config.cms}' is not a recognised type")

    return report
