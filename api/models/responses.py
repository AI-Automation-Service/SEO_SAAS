from typing import Optional
from pydantic import BaseModel


class ProjectSummary(BaseModel):
    name: str
    website: str
    business_name: str
    cms: str
    active: bool


class ProjectDetail(BaseModel):
    name: str
    website: str
    business_name: str
    business_type: str
    country: str
    language: str
    cms: str
    seo_plugin: Optional[str]
    image_source: str
    active: bool
    knowledge_files: list[str]
    competitors: list[str] = []
    tone_of_voice: str = ""
    target_audience: str = ""
    seo_goals: list[str] = []
    business_goals: list[str] = []
    primary_conversion: str = ""
    business_location: str = ""


class ValidationResult(BaseModel):
    project: str
    valid: bool
    errors: list[str]
    warnings: list[str]


class ProjectCreated(BaseModel):
    name: str
    path: str
    message: str


class SkillInfo(BaseModel):
    name: str


class HealthResponse(BaseModel):
    status: str
    service: str
