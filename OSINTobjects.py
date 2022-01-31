from attrs import define, field

from datetime import datetime, timezone

@define(kw_only=True)
class Article:
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
    inserted_at: datetime = field(default=datetime.now(timezone.utc).astimezone())
    saved: bool = False
    read: bool = False

    def as_dict(self):
        return { "title" : self.title,
                 "description" : self.description,
                 "content" : self.content,
                 "formatted_content" : self.formatted_content,

                 "url" : self.url,
                 "image_url" : self.image_url,
                 "author" : self.author,
                 "profile" : self.profile,
                 "source" : self.source,

                 "publish_date" : self.publish_date,
                 "inserted_at" : self.inserted_at,

                 "tags" : self.tags
               }
