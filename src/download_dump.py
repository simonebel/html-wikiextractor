from argparse import ArgumentParser, Namespace
from pathlib import Path
from urllib.request import urlretrieve

import bs4
import requests

from utils.log import get_log

WIKI_HTML_URL = "https://dumps.wikimedia.org/other/enterprise_html/runs"

DUMP_SUFFIX = "ENTERPRISE-HTML.json.tar.gz"

logger = get_log(__file__)


def report_download(
    block_count: int,
    block_size: int,
    total_size: int,
    report_period: int = 10000,
) -> None:
    """
    Report the current progress of the download
    """
    current_size = (block_count * block_size) / (1024**3)
    total_size = total_size / (1024**3)

    if block_count > 0 and block_count % report_period == 0:
        progress = current_size / total_size
        logger.info(f"Downloaded {current_size:.2f}/{total_size:.2f} ~ {progress:.2f}%")


def main(args: Namespace) -> None:
    """
    Download a Wikipeida HTML dump
    """
    output = Path(args.output)
    output.mkdir(exist_ok=True, parents=True)

    response = requests.get(WIKI_HTML_URL)

    if response.status_code == 200:
        soup = bs4.BeautifulSoup(response.text, "html.parser")
        links = soup.find_all("a")

        if links:
            latest = links[-1].text[:-1]
            filename = f"{args.lang}wiki-NS{args.namespace}-{latest}-{DUMP_SUFFIX}"
            dump_link = f"{WIKI_HTML_URL}/{latest}/{filename}"

            logger.info(f"Start downloading {dump_link}")
            urlretrieve(
                dump_link, output.joinpath(filename), reporthook=report_download
            )
        else:
            raise ValueError("Unable to get latest link")

    else:
        raise requests.HTTPError("Can't requests the dump url")


if __name__ == "__main__":
    parser = ArgumentParser(
        "Download a Wikipedia dump from https://dumps.wikimedia.org/other/enterprise_html/runs/",
    )

    parser.add_argument("output", help="The output directory.")

    output_group = parser.add_argument_group(
        title="Output", description="Arguments related to output."
    )

    output_group.add_argument(
        "--lang",
        "-l",
        help="Which language to dowload the dump for",
        required=True,
    )
    output_group.add_argument(
        "--namespace",
        "-ns",
        choices=[0, 6, 10],
        default=0,
        help="Which namespace to dowload the dump for",
    )

    args = parser.parse_args()

    main(args)
