from io import StringIO

from modules.objects import FullArticle

# Function for taking in some details about an articles and creating a markdown file with those
def convert_article_to_md(article: FullArticle) -> StringIO:

    article_file = StringIO()

    article_file.write(f"# {article.title}\n")
    article_file.write(f"## {article.description}\n\n")
    article_file.write("## Information:\n")

    # Convert the link for the article to markdown format
    md_source_url = f"[article]({article.url})"

    detail_labels = ["Source: ", "Link: ", "Date: ", "Author: "]
    for i, detail in enumerate(
        [article.source, md_source_url, article.publish_date, article.author]
    ):
        article_file.write(f"+ {detail_labels[i]} {str(detail)}" + "\n")

    article_file.write("\n## Article:\n")
    article_file.write(f"![Article Image]({article.image_url})" + "\n")

    if article.formatted_content:
        article_file.write(article.formatted_content)

    article_file.write("\n## Tags:\n")

    if "manual" in article.tags and article.tags["manual"] != {}:
        article_file.write(
            "\n"
            + "\n\n".join(
                [
                    f"#### {category.capitalize()}:\n"
                    + " ".join(
                        [f"[[{tag}]]" for tag in article.tags["manual"][category]]
                    )
                    for category in article.tags["manual"]
                ]
            )
            + "\n"
        )

    if "interresting" in article.tags:
        article_file.write("\n### Objects of interrest:\n\n")
        for object_name in article.tags["interresting"]:

            article_file.write(
                f"#### {object_name}\n[[{']] [['.join(article.tags['interresting'][object_name]['results'])}]]\n\n"
                if article.tags["interresting"][object_name]["tag"]
                else f"#### {object_name}\n{' '.join(article.tags['interresting'][object_name]['results'])}\n\n"
            )

    if "automatic" in article.tags:
        article_file.write("\n### Autogenerated Tags:\n\n")
        article_file.write(
            "[["
            + "]] [[".join(article.tags["automatic"])
            + "]] [["
            + article.source
            + "]]"
        )

    return article_file
