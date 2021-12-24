from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass
class Article:
    title: str 
    description: str
    url: str
    profile: str
    id: str = ""
    image_url: str = ""
    author: str = ""
    article_contents = ""
    tags: dict[str] = field(default_factory=dict)
    inserted_at: datetime = field(default=datetime.now(timezone.utc).astimezone())
    publish_date: datetime = field(default=datetime.now(timezone.utc).astimezone())

    def as_dict(self):
        return { "title" : self.title,
                 "description" : self.description,
                 "contents" : self.article_contents,

                 "url" : self.url,
                 "image_url" : self.image_url,
                 "author" : self.author,
                 "profile" : self.profile,

                 "publish_date" : self.publish_date,
                 "inserted_at" : self.inserted_at,

                 "tags" : self.tags
               }
