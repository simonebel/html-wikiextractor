from argparse import ArgumentParser

if __name__ == "__main__":
    parser = ArgumentParser(
        "Download a Wikipedia dump from https://dumps.wikimedia.org/other/enterprise_html/runs/",
    )

    parser.add_argument("outpout", help="The output directory.")

    output_group = parser.add_argument_group(
        title="Output", description="Arguments related to output."
    )
    output_group.add_argument(
        "--latest",
        default=True,
        action="store_true",
        help="Whether to download the latest dump.",
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
    # res = requests.get(
    #     "https://dumps.wikimedia.org/other/enterprise_html/runs/20240101/"
    # )

    # s = BeautifulSoup(res.text, "html.parser")
    # pre = s.find("pre")

    # c = 2
    # data = []
    # row = []
    # for tag in pre:
    #     row.append(tag.text.strip())
    #     c -= 1
    #     if c == 0:
    #         data.append(row)
    #         row = []
    #         c = 2

    # main_wiki = []
    # for row in data:
    #     if "wiki-NS0-20240101-ENTERPRISE-HTML.json.tar.gz" in row[0]:
    #         main_wiki.append(row)

    # domain_size = []
    # for domain, metadata in main_wiki:
    #     idx = domain.index("wiki")
    #     lang = domain[:idx]
    #     size = int(metadata.split(" ")[-1]) / (1024**3)

    #     domain_size.append((lang, size))

    # with open("./wiki_domain_size_GB.txt", "w") as f:
    #     for domain, size in domain_size:
    #         f.write(f"{domain}\t{size}\n")

    domain_size = []
    with open("./wiki_domain_size_GB.txt", "r") as f:
        lines = f.read().splitlines()
        for line in lines:
            domain, size = line.split("\t")
            domain_size.append((domain, float(size)))

    sorted_domain_size = sorted(domain_size, key=lambda x: x[1])
    print(sorted_domain_size)
