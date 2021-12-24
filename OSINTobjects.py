from dataclasses import dataclass, field, KW_ONLY
from datetime import datetime, timezone

@dataclass
class Article:
    _: KW_ONLY
    title: str 
    description: str
    url: str
    profile: str
    publish_date: datetime
    id: str = ""
    image_url: str = ""
    author: str = ""
    contents: str = ""
    tags: dict[str] = field(default_factory=dict)
    inserted_at: datetime = field(default=datetime.now(timezone.utc).astimezone())

    def as_dict(self):
        return { "title" : self.title,
                 "description" : self.description,
                 "contents" : self.contents,

                 "url" : self.url,
                 "image_url" : self.image_url,
                 "author" : self.author,
                 "profile" : self.profile,

                 "publish_date" : self.publish_date,
                 "inserted_at" : self.inserted_at,

                 "tags" : self.tags
               }
