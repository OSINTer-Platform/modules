from pydantic import BaseModel, HttpUrl
from typing import Dict, List, Union, Optional
from datetime import datetime, timezone

class BaseArticle(BaseModel):
    title: str
    description: str
    url: HttpUrl
    profile: str
    source: str
    publish_date: datetime
    inserted_at: datetime = datetime.now(timezone.utc)
    id: Optional[str] = None

class FullArticle(BaseArticle):
    image_url: Optional[HttpUrl] = None
    author: Optional[str] = None
    formatted_content: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    tags: Optional[Dict[str, Union[ List[str],
                           Dict[str, Union[ List[str],
                                            Dict[str, Union [List[str], bool] ]
                                              ]
                                    ]
                             ]
                   ]
          ] = {}
    read_times: int = 0
    similar: List[int] = None


class BaseTweet(BaseModel):
    twitter_id: str
    content: str

    publish_date: datetime
    inserted_at: datetime = datetime.now(timezone.utc)

    id: Optional[str] = None

class FullTweet(BaseTweet):
    hashtags: List[str] = []
    mentions: List[str] = []

    author_details: Dict[str, str] = {}
    OG: Dict[str, str] = {}

    read_times: int = 0
