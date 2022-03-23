from attrs import define, field

from datetime import datetime, timezone

dateFormat = "%Y-%m-%dT%H:%M:%S%z"

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
    inserted_at: datetime = field(default=datetime.now(timezone.utc))
    saved: bool = False
    read: bool = False
    read_times: int = 0

    def as_dict(self):
        return { "id" : self.id,
                 "title" : self.title,
                 "description" : self.description,
                 "content" : self.content,
                 "formatted_content" : self.formatted_content,

                 "url" : self.url,
                 "image_url" : self.image_url,
                 "author" : self.author,
                 "profile" : self.profile,
                 "source" : self.source,

                 "publish_date" : self.publish_date.strftime(dateFormat),
                 "inserted_at" : self.inserted_at.strftime(dateFormat),

                 "read_times" : self.read_times,

                 "tags" : self.tags
               }

@define(kw_only=True)
class Tweet:
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

    def as_dict(self):
        return { "twitter_id" : self.twitter_id,
                 "content" : self.content,

                 "hashtags" : self.hashtags,
                 "mentions" : self.mentions,

                 "author_details" : self.author_details,
                 "OG" : self.OG,

                 "publish_date" : self.publish_date.strftime(dateFormat),
                 "inserted_at" : self.inserted_at.strftime(dateFormat),

                 "read_times" : self.read_times,

                 "id" : self.id
               }
