from fastapi import APIRouter

from api.models.responses import SkillInfo
from skills.base import SkillLoader

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[SkillInfo])
def list_skills():
    loader = SkillLoader()
    return [SkillInfo(name=name) for name in loader.list_skills()]
