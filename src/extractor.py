import gzip
import heapq
import json
import queue
import re
import sys
import time
from argparse import ArgumentParser, Namespace
from dataclasses import dataclass, field
from multiprocessing import Manager, Process, cpu_count
from pathlib import Path
from statistics import mean
from typing import List

import bs4

from table import contains_table, extract
from tree import NavigableTree
from utils.log import get_log
from utils.text import clean_html_text, strip_line_escape

logger = get_log(__file__)


class Section:
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
            tag: bs4.element.Tag

            if tag.name in cls.title_tag:
                section_title = tag.text

            elif cls.include_table and contains_table(tag):
                table = extract(tag)
                if table:
                    tables.append(table)

            elif tag.name == "ul" or tag.name == "ol" or tag.name == "dl":
                if cls.include_list:
                    body.append(tag.text)
            elif tag.name == "p":
                body.append(tag.text)

            elif tag.name == "link":
                pass

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

    def parse(self) -> str:
        body, tables = f"{self.title}\n\n", []
        for section in self.sections:
            section_body = clean_html_text("\n".join(section.body))

            if section_body:
                body += f"{section.title}.\n" if section.title else "\n"
                body += f"{section_body}\n" if section_body else "\n"

            if section.tables:
                for table in section.tables:
                    table["description"] = self.description
                    table["section_title"] = section.title
                    table["section_text"] = section_body

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
                out["tables"] = tables

            return json.dumps(out)

        elif self.to_html:
            return f'<doc id="{self.id}" url="{self.url}" title={self.title}>\n{body}\n</doc>'

    def __repr__(self) -> str:
        return f"Article(title:'{self.title} sections:{len(self.sections)}')"


@dataclass
class StatisticsCollector:
    output: str
    latencies: List[float] = field(default_factory=list)
    start = time.time()

    @property
    def num_articles(self) -> int:
        return len(self.latencies)

    def track(self):
        end = time.time()
        self.latencies.append(end - self.start)
        self.start = time.time()

    def write(self) -> None:
        stats = {
            "articles": self.num_articles,
            "overall (s)": sum(self.latencies),
            "latency_mean (s)": mean(self.latencies),
        }
        with Path(self.output, "stats.csv").open("w") as f:
            f.write(json.dumps(stats))


class RotatingOutput:
    def __init__(self, output, max_size: int = 20 * 1024, max_files: int = 100) -> None:
        self.max_size = max_size
        self.max_files = max_files
        self.output = output

        self.dir_count = 0
        self.file_count = 0
        self.current_out = 1

        self.file = Path(self.output, self._dir(), f"wiki_{self.file_count}").open("w")

    def _dir(self):
        if self.dir_count == 0:
            Path(self.output, str(self.current_out)).mkdir(exist_ok=True, parents=True)

        elif self.dir_count + 1 > self.max_files:
            self.current_out += 1
            self.dir_count = 0
            Path(self.output, self._dir()).mkdir(exist_ok=True, parents=True)

        return str(self.current_out)

    def write(self, data: str):
        current_dir = self._dir()

        d = bytes(data.encode())
        current_size = self.file.tell() + len(d)

        if current_size > self.max_size:
            self.file_count += 1
            self.file.close()

            self.file = Path(self.output, current_dir, f"wiki_{self.file_count}").open(
                "w"
            )

        self.file.write(data)

    def close(self):
        self.file.close()

    def flush(self):
        self.file.flush()


def write_out(
    out_queue: queue.Queue,
    output: RotatingOutput,
    statistics_collector: StatisticsCollector,
):
    h = []
    current_priority = 0
    while 1:
        min_heap = heapq.nsmallest(1, h)
        if min_heap:
            (min_heap,) = min_heap
            priority, _ = min_heap
            if priority == current_priority:
                _, article = heapq.heappop(h)
                output.write(f"{article}\n")
                current_priority += 1
                statistics_collector.track()

        try:
            article, lx = out_queue.get(block=False)
        except queue.Empty:
            continue

        if article:
            heapq.heappush(h, (lx, article))

        if len(h) == 0 and current_priority > 0 and article is None:
            output.close()
            break

    statistics_collector.write()


def process_dump(queue: queue.Queue, out_queue: queue.Queue):
    while 1:
        line, lx = queue.get()

        if not line:
            break

        json_article = json.loads(line)
        tree = NavigableTree.build(json_article["article_body"]["html"])

        article = Article(
            id=json_article["identifier"],
            url=json_article["url"],
            title=json_article["name"],
            sections=[Section.parse(content=node.content) for node in tree],
        )

        out_queue.put((article.parse(), lx))


def main(args: Namespace) -> None:
    workers = cpu_count()
    if args.dev:
        workers = min(args.dev, workers - 2)

    logger.info(f"Using {workers} processes for extraction")

    manager = Manager()
    job_queue = manager.Queue(workers)
    output_queue = manager.Queue(workers)

    if args.stdout:
        output = sys.stdout
    else:
        output = RotatingOutput(args.output)

    statistics_collector = StatisticsCollector(output=args.output)
    reduce = Process(
        target=write_out, args=(output_queue, output, statistics_collector)
    )
    reduce.start()

    pool = []
    for _ in range(workers):
        p = Process(target=process_dump, args=(job_queue, output_queue))
        p.daemon = True
        p.start()
        pool.append(p)

    start = time.time()
    input = Path(args.input_file)

    with gzip.open(input, mode="rb") as f:
        for lx, line in enumerate(f):
            if args.dev == lx:
                break

            l = line.decode()
            json_match = re.search(r"[{]", l)
            if json_match:
                _, e = json_match.span()
                valid_raw_json = l[e - 1 :]
                job_queue.put((valid_raw_json, lx))
            else:
                logger.error("Invalid JSON")

    for _ in range(workers):
        job_queue.put((None, None))

    for p in pool:
        p.join()
        logger.info(f"Map {p.name} end")

    output_queue.put((None, None))
    reduce.join()
    logger.info(f"Reduce {reduce.name} end")

    logger.info(f"Reading all dumps took {time.time()-start}")


if __name__ == "__main__":
    parser = ArgumentParser(
        "Extract and write to disk table and infobox from a HTML wikipedia dumps",
    )

    parser.add_argument("input_file", help="The input HTML dump.")

    formatting_group = parser.add_argument_group(
        title="Formatting", description="Arguments related to output formatting."
    )
    formatting_group.add_argument(
        "--include_table",
        default=False,
        action="store_true",
        help="Whether to include the tables or not.",
    )
    formatting_group.add_argument(
        "--include_list",
        default=False,
        action="store_true",
        help="Whether to include the lists or not.",
    )
    formatting_group.add_argument(
        "--include_link",
        default=False,
        action="store_true",
        help="Whether to include the slinks or not.",
    )

    output_group = parser.add_argument_group(
        title="Output", description="Arguments related to output."
    )
    output_group.add_argument(
        "--output",
        help="The output directory",
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
