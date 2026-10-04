from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Literal

TERMS = "2026-10-04"
CATEGORIES = [
    "租房合租",
    "职场打工",
    "通勤日常",
    "生活搭子",
    "情绪树洞",
    "城市怪谈",
    "故事连载",
    "生活求助",
    "随手碎片",
    "厨房日常",
]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Consent(Input):
    accepted_terms: str


class CreatePost(Input):
    title: str = Field(min_length=2, max_length=80)
    body: str = Field(min_length=5, max_length=3000)
    category: str

    @field_validator("category")
    @classmethod
    def valid_category(cls, v):
        if v not in CATEGORIES:
            raise ValueError("请选择正确的版块")
        return v


class CreateComment(Input):
    body: str = Field(min_length=1, max_length=1000)


class Vote(Input):
    liked: bool


class ReportInput(Input):
    target_type: Literal["post", "comment"]
    target_id: str = Field(min_length=36, max_length=36)
    reason: str = Field(min_length=2, max_length=300)


class BlockInput(Input):
    target_type: Literal["post", "comment"] = "post"
    target_id: str = Field(min_length=36, max_length=36)


class FeedbackInput(Input):
    kind: Literal["bug", "idea", "safety"]
    body: str = Field(min_length=5, max_length=2000)
    device: str = Field(default="", max_length=150)
    app_version: str = Field(default="1.0.0", max_length=30)


class ModerateInput(Input):
    target_type: Literal["post", "comment"]
    target_id: str = Field(min_length=36, max_length=36)
    decision: Literal["approve", "hide"]
    note: str = Field(min_length=2, max_length=300)
    public_reason: str = Field(default="", max_length=300)


class FeedbackReply(Input):
    status: Literal["new", "reviewing", "planned", "resolved", "declined"]
    response: str = Field(max_length=2000)
