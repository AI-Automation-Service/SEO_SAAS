from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class PostDraft:
    title: str
    content: str
    slug: str = ""
    meta_description: str = ""
    tags: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    status: str = "draft"


@dataclass
class PublishedPost:
    id: str | int
    url: str
    title: str
    status: str


class CMSAdapter(ABC):
    @abstractmethod
    def test_connection(self) -> bool: ...

    @abstractmethod
    def create_post(self, draft: PostDraft) -> PublishedPost: ...

    @abstractmethod
    def get_posts(self, page: int = 1, per_page: int = 100) -> list[dict]: ...

    @abstractmethod
    def get_sitemap_urls(self) -> list[str]: ...
