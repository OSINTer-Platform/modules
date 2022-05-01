from attrs import define, field

from datetime import datetime, timezone

dateFormat = "%Y-%m-%dT%H:%M:%S%z"

class base():
    def as_dict(self):
        object_dict = {}

        for attr in dir(self):
            attrValue = getattr(self, attr)
            if not attr.startswith("__") and not callable(getattr(self, attr)) and attrValue:
                if isinstance(attrValue, datetime):
                    object_dict[attr] = attrValue.strftime(dateFormat)
                else:
                    object_dict[attr] = attrValue

        return object_dict



@define(kw_only=True)
class Article(base):
    title: str
    description: str
    url: str
    profile: str
    source: str
    publish_date: datetime
    id: str = ""
    image_url: str = ""
    author: str = ""
    formatted_content: str = ""
    content: str = ""
    summary: str = ""
    tags: dict = field(factory=dict)
    inserted_at: datetime = field(default=datetime.now(timezone.utc))
    saved: bool = False
    read: bool = False
    read_times: int = 0
    similar: list = field(factory=list)

@define(kw_only=True)
class Tweet(base):
    twitter_id: str
    content: str

    hashtags: list = field(factory=list)
    mentions: list = field(factory=list)

    author_details: dict
    OG: dict = field(factory=dict)

    publish_date: datetime
    inserted_at: datetime = field(default=datetime.now(timezone.utc))

    read_times: int = 0

    id: str = ""
