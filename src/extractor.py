import json
import unicodedata
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Dict

import requests
from bs4 import BeautifulSoup

# French wikipedia :
#   - Infobox v2 : Infoboxes are a single table (https://fr.wikipedia.org/wiki/Projet:Infobox/V2)
#   - Infobox v3 : Infoboxes are div containing multiple tables (https://fr.wikipedia.org/wiki/Projet:Infobox/V3)

# For other wiki :
# Infobox : Single table
#   - en : https://en.wikipedia.org/wiki/Wikipedia:WikiProject_Infoboxes


def clean_html_text(text: str):
    return unicodedata.normalize("NFKD", text)


def process_article(article: Dict[str, str]) -> Dict:
    html_content = BeautifulSoup(article["article_body"]["html"], "html.parser")

    # title = html_content.find("title")
    # article_title = clean_html_text(title.text)

    for section in html_content.find_all("section"):
        print(section)
        print("end")
        print()

    # infobox = html_content.find("div", {"class": "infobox_v3"})
    # infobox_data = []
    # for tag in infobox:
    #     # print(tag.find_all("th"))
    #     # print(tag.find_all("span"))

    #     rows = tag.find_all("tr")

    #     if rows:
    #         for row in rows:
    #             header = row.find("th")
    #             print(header.text)
    #             cell = row.find("td")
    #             cell_content = []
    #             for tag in cell.find("div"):
    #                 if tag.name == None:
    #                     if tag.text:
    #                         if tag.text != "\n":
    #                             cell_content.append(tag.text)

    #                 elif tag.name == "span":
    #                     cell_content.append(tag.text)
    #                 elif tag.name == "br":
    #                     cell_content.append("\n")

    #             infobox_data.append(
    #                 [
    #                     {"type": "header", "value": clean_html_text(header.text)},
    #                     {
    #                         "type": "cell",
    #                         "value": clean_html_text("".join(cell_content)),
    #                     },
    #                 ]
    #             )
    # print(infobox_data)
    # print(article.keys())
    # print(article["categories"])

    # article_data = {
    #     "id": article["identifier"],
    #     "url": article["url"],
    #     "title": article["name"],
    # }


infoboxes_map = {}

import pickle as pkl

# https://fr.wikipedia.org/wiki/2e_division_cuirass%C3%A9e
# https://fr.wikipedia.org/wiki/Abbaye_Saint-Martin_d%27%C3%89pernay


def collect_infobox_data(article):
    global infoboxes_map
    url = article["url"]
    body = article["article_body"]["html"]
    if "infobox_v2" in body:
        infoboxes_map[url] = body


def process_file(file: Path):
    with file.open() as f:
        for line in f:
            article = json.loads(line)
            process_article(article)
            break
    #         collect_infobox_data(article)
    #         if len(infoboxes_map) == 10000:
    #             break

    # with open("/media/simon/T7/wikipedia/infoboxes.bin", "wb") as g:
    #     pkl.dump(infoboxes_map, g)


def main(args: Namespace) -> None:
    path = Path(args.input_file)

    # with open("/media/simon/T7/wikipedia/infoboxes.bin", "rb") as g:
    #     infoboxes_map = pkl.load(g)
    #     print(infoboxes_map.keys())

    for file in path.rglob("*.ndjson"):
        process_file(file)
        break


if __name__ == "__main__":
    # https://dumps.wikimedia.org/other/enterprise_html/runs/20240101/
    parser = ArgumentParser(
        "Extract and write to disk table and infobox from a HTML wikipedia dumps"
    )

    parser.add_argument(
        "input_file", help="The input directory containing the extracted file."
    )

    args = parser.parse_args()

    # main(args)
