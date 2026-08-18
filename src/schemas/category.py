from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CategoryItem(BaseModel):
    id: str
    name: str
    parent_id: Optional[str] = None
    level: int
    path: list[str] = Field(default_factory=list)


class CategoryTreeNode(CategoryItem):
    children: list["CategoryTreeNode"] = Field(default_factory=list)


CategoryTreeNode.model_rebuild()
