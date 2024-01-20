import argparse
import gzip
import json
import queue
import re
import time
import unicodedata
import zlib
from argparse import ArgumentParser, Namespace
from multiprocessing import Manager, Process, cpu_count
from pathlib import Path
from typing import Dict, List, Tuple

import bs4
import requests

from tree import NavigableTree
from utils.log import get_log

logger = get_log(__file__)


INFOBOX_STRUCT = [
    ("div", "infobox_v3"),
    ("table", "infobox_v2"),
    ("table", "infobox"),
]

INFOBOX_TYPES = {"infobox_v3", "infobox_v2", "infobox"}


def clean_html_text(text: str):
    return unicodedata.normalize("NFKD", text).strip()


def strip_line_escape(body: List[str]):
    while len(body) > 0 and (body[-1] == "\n" or body[-1] == ""):
        body.pop()
    while len(body) > 0 and (body[0] == "\n" or body[0] == ""):
        body.pop(0)

    return body


def _contains_table(tag: bs4.element.Tag) -> Tuple[bool, str]:
    """
    Check wether a section contains a table or an infobox. If so, also return the type of the table.
    """
    for tag_name, class_name in INFOBOX_STRUCT:
        if (
            tag.name == tag_name
            and "class" in tag.attrs
            and class_name in tag.attrs["class"]
        ):
            return True

    if tag.name == "table":
        return True

    return False


class TableExtractor:
    def _parse_tag_DFO(self, tag: bs4.element.Tag) -> str:
        """
        Parse a tag in DFO order
        """
        nodes = [tag]
        content = []
        while len(nodes) > 0:
            current = nodes.pop(0)
            if hasattr(current, "children"):
                if current.name == "br":
                    content.append("\n")
                nodes = list(current.children) + nodes

            else:
                content.append(current)

        return clean_html_text("".join(strip_line_escape(content)))

    def _parse_tr(self, tr: bs4.element.Tag) -> List[Dict[str, str]]:
        row = []
        for cell in tr:
            if hasattr(cell, "name"):
                if cell.name == "th":
                    row.append(
                        {
                            "type": "header",
                            "value": self._parse_tag_DFO(cell),
                        }
                    )
                elif cell.name == "td":
                    row.append(
                        {
                            "type": "cell",
                            "value": self._parse_tag_DFO(cell),
                        }
                    )

        return row

    def extract_infobox_v2(self, infobox_html: bs4.element.Tag):
        """
        Extract an infobox of type V2 (https://fr.wikipedia.org/wiki/Projet:Infobox/V2)
        """
        tbody = infobox_html.find("tbody")
        data, images = [], set()
        for tr in tbody:
            row = self._parse_tr(tr)
            if row:
                data.append(row)

            # img_tag = tag.find("img")
            # if img_tag:
            #     if "src" in img_tag.attrs:
            #         src = f"https:{img_tag.attrs['src']}"
            #         if src not in images:
            #             images.add(src)

        return {
            "title": data.pop(0)[0]["value"],
            "data": data,
            "images": images,
            "type": "infobox",
        }

    def extract_infobox_v3(self, infobox_html: bs4.element.Tag):
        """
        Extract an infobox of type V3 (https://fr.wikipedia.org/wiki/Projet:Infobox/V3).
        """
        title, images, data = "", set(), []
        for tag in infobox_html:
            # img_tag = tag.find("img")
            # if img_tag:
            #     if "src" in img_tag.attrs:
            #         src = f"https:{img_tag.attrs['src']}"
            #         if src not in images:
            #             images.add(src)

            if tag.name == "table":
                table_caption = tag.find("caption")
                if table_caption:
                    data.append(
                        [
                            {
                                "type": "header",
                                "value": clean_html_text(table_caption.text),
                            }
                        ]
                    )

                tbody = tag.find("tbody")
                if tbody:
                    for tr in tbody:
                        row = self._parse_tr(tr)
                        if row:
                            data.append(row)

                else:
                    logger.error("Table without tbody")
            else:
                if tag.text:
                    data.append(
                        {
                            "type": "header",
                            "value": clean_html_text(tag.text),
                        }
                    )

        return {
            "title": data.pop(0)["value"],
            "data": data,
            "images": images,
            "type": "infobox",
        }

    def extract_infobox():
        """
        Extract an infobox see (https://en.wikipedia.org/wiki/Wikipedia:WikiProject_Infoboxes)
        """
        pass

    def extract_table(self, html_table: bs4.element.Tag):
        """
        Extract a classical HTML table.
        """
        html_caption = html_table.find("caption")
        title = html_caption.text if html_caption else ""
        data = []
        tbody = html_table.find("tbody")
        for tr in tbody:
            row = self._parse_tr(tr)
            if row:
                data.append(row)

        return {"title": title, "data": data, "type": "table"}

    def extract(self, table: bs4.element.Tag):
        """
        Factory method for extracting a table or an infobox
        """
        table_type = "table"
        if "class" in table.attrs:
            class_names = table.attrs["class"]
            for class_name in class_names:
                if class_name in INFOBOX_TYPES:
                    table_type = class_name

        if table_type == "infobox_v3":
            return self.extract_infobox_v3(table)

        elif table_type == "infobox_v2":
            return self.extract_infobox_v2(table)

        elif table_type == "infobox":
            return self.extract_infobox(table)

        elif table_type == "table":
            return self.extract_table(table)

        else:
            raise ValueError(
                f'Unknown extraction type {table_type}. Extraction type should be one of ["infobox_v3", "infobox_v2", "infobox", "table"] '
            )


class Section:
    table_extractor = TableExtractor()

    title_tag = {f"h{i}" for i in range(1, 7)}

    include_list: bool = False

    include_table: bool = False

    def __init__(self, title: str, body: str, tables: List) -> None:
        self.title = title
        self.body = body
        self.tables = tables

    @classmethod
    def parse(cls, content: bs4.element.Tag):
        section_title, body, tables = "", [], []
        for tag in content:
            if tag.name in cls.title_tag:
                section_title = tag.text

            elif cls.include_table and _contains_table(tag):
                table = cls.table_extractor.extract(tag)
                if table:
                    tables.append(table)

            # Can be simplify
            elif tag.name != "section":
                if tag.name == "ul" or tag.name == "ol" or tag.name == "dl":
                    if cls.include_list:
                        body.append(tag.text)
                elif tag.name == "p":
                    body.append(tag.text)

        return cls(
            title=section_title,
            body=strip_line_escape(body),
            tables=tables,
        )

    def __repr__(self) -> str:
        return f"Section(title:'{self.title}' body:{self.body} tables:{self.tables})"


class Article:
    to_json: bool = True

    to_html: bool = True

    def __init__(self, id: str, url: str, title: str, sections: List[Section]) -> None:
        self.id = id
        self.url = url
        self.title = title
        self.sections = sections

    @property
    def description(self):
        return clean_html_text("".join(self.sections[0].body))

    def parse(
        self,
    ) -> str:
        body, tables = f"{self.title}\n\n", []
        for section in self.sections:
            section_body = clean_html_text("\n".join(section.body))

            if section_body:
                body += f"{section.title}.\n" if section.title else "\n"
                body += f"{section_body}\n" if section_body else "\n"

            if section.tables:
                for table in section.tables:
                    table["description"] = self.description
                    table["segment_title"] = section.title
                    table["segment_text"] = section_body

                tables.extend(section.tables)

        body = body.strip()

        if self.to_json:
            out = {
                "id": self.id,
                "url": self.url,
                "title": self.title,
                "body": body,
            }

            if tables:
                out["tables"] = table

            return json.dumps(out)

        elif self.to_html:
            return f'<doc id="{self.id}" url="{self.url}" title={self.title}>\n{body}\n</doc>'

    def __repr__(self) -> str:
        return f"Article(title:'{self.title} sections:{len(self.sections)}')"


def write_out(queue: queue.Queue):
    output = Path("./out")
    if output.exists():
        output.unlink()

    f = output.open("w")
    while 1:
        article = queue.get()
        logger.error(article)
        if not article:
            f.close()
            break

        f.write(f"{article}\n")


def process_dump(queue: queue.Queue, out_queue: List[str]):
    while 1:
        line = queue.get()

        if not line:
            break

        json_article = json.loads(line)
        tree = NavigableTree()
        tree.build(json_article["article_body"]["html"])

        article = Article(
            id=json_article["identifier"],
            url=json_article["url"],
            title=json_article["name"],
            sections=[Section.parse(content=node.content) for node in tree],
        )

        out_queue.put(article.parse())


# def process_file(file: Path, report_period=1):
#     processed = 0
#     with file.open() as f:
#         for line in f:
#             process_article(line)

#             processed += 1

#             if processed % report_period == 0:
#                 logger.info(f"Processed {processed} articles")


def main(args: Namespace) -> None:
    workers = cpu_count()
    if args.dev:
        workers = min(args.dev, workers - 1)

    manager = Manager()
    job_queue = manager.Queue(workers)
    output_queue = manager.Queue(workers)

    reduce = Process(target=write_out, args=(output_queue,))
    reduce.start()

    pool = []
    for _ in range(workers):
        p = Process(target=process_dump, args=(job_queue, output_queue))
        p.daemon = True
        p.start()
        pool.append(p)

    start = time.time()
    input = Path(args.input_file)

    line_count = 0
    with gzip.open(input, mode="rb") as f:
        for line in f:
            l = line.decode()
            m = re.search(r"[{]", l)
            if m:
                s, e = m.span()
                valid_raw_json = l[e - 1 :]
                job_queue.put(valid_raw_json)
                line_count += 1
            else:
                logger.error("Invalid JSON")

            if args.dev and args.dev == line_count:
                break

    for _ in range(workers):
        job_queue.put(None)

    for p in pool:
        p.join()
        logger.info(f"{p} end")

    output_queue.put(None)
    reduce.join()

    logger.info(f"{reduce} end")

    logger.info(f"Reading all dumps took {time.time()-start}")


if __name__ == "__main__":
    # https://dumps.wikimedia.org/other/enterprise_html/runs/20240101/
    parser = ArgumentParser(
        "Extract and write to disk table and infobox from a HTML wikipedia dumps",
    )

    parser.add_argument("input_file", help="The input HTML dump.")
    # parser.add_argument(
    #     "--compressed", help="The input directory containing the extracted file."
    # )

    output_group = parser.add_argument_group(
        title="Output", description="Arguments related to output."
    )
    output_group.add_argument(
        "--include_table",
        default=False,
        action="store_true",
        help="Whether to include the tables or not.",
    )
    output_group.add_argument(
        "--include_list",
        default=False,
        action="store_true",
        help="Whether to include the lists or not.",
    )
    output_group.add_argument(
        "--json",
        default=True,
        action="store_true",
        help="Whether to write the articles on disk in JSON",
    )
    output_group.add_argument(
        "--html",
        default=False,
        action="store_true",
        help="Whether to write the articles on disk in HTML",
    )
    output_group.add_argument(
        "--stdout",
        default=False,
        action="store_true",
        help="Whether to redirect the article to the stdout",
    )

    dev_group = parser.add_argument_group(
        title="Dev", description="Arguments related to debug this script"
    )
    dev_group.add_argument(
        "--dev",
        type=int,
        help="Whether to run this script in dev mode. This argument expect an int which will be the size of the number of articles to parse",
    )
    args = parser.parse_args()

    Section.include_list = args.include_list
    Section.include_table = args.include_table
    Article.to_json = args.json
    Article.to_json = args.html

    main(args)

    # Text output
    # No break line between paragraph of sections
    # No Notes/ References ...
    # If a section has no content do not include the title
