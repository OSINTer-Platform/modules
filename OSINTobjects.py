from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass
class Article:
    id: str
    title: str 
    description: str
    url: str
    profile: str
    scraped: bool
    image_url: str = ""
    author: str = ""
    file_path = ""
    article_contents = ""
    tags: dict[str] = field(default_factory=dict)
    inserted_at: datetime = field(default=datetime.now(timezone.utc).astimezone())
    publish_date: datetime = field(default=datetime.now(timezone.utc).astimezone())

    def as_dict(self):
        return {"id" : self.id,
                "details" : {   "title" : self.title,
                                "description" : self.description,
                                "url" : self.url,
                                "image_url" : self.image_url,
                                "author" : self.author,
                                "publish_date" : self.publish_date.strftime("%Y/%m/%d %H:%M:%S%z")
                            },
                "scraped" : self.scraped,
                "file_path" : self.file_path,
                "contents" : self.article_contents,
                "tags" : self.tags,
                "inserted_at" : self.inserted_at.strftime("%Y/%m/%d %H:%M:%S%z")}

