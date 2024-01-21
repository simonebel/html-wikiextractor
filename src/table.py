from typing import Dict, List, Tuple

import bs4

from utils.log import get_log
from utils.text import clean_html_text, strip_line_escape

logger = get_log(__file__)

INFOBOX_STRUCT = [
    ("div", "infobox_v3"),
    ("table", "infobox_v2"),
    ("table", "infobox"),
]

INFOBOX_TYPES = {"infobox_v3", "infobox_v2", "infobox"}


def _parse_tag_DFO(tag: bs4.element.Tag) -> str:
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


def _parse_tr(tr: bs4.element.Tag) -> List[Dict[str, str]]:
    row = []
    for cell in tr:
        if hasattr(cell, "name"):
            if cell.name == "th":
                row.append(
                    {
                        "type": "header",
                        "value": _parse_tag_DFO(cell),
                    }
                )
            elif cell.name == "td":
                row.append(
                    {
                        "type": "cell",
                        "value": _parse_tag_DFO(cell),
                    }
                )

    return row


def contains_table(tag: bs4.element.Tag) -> Tuple[bool, str]:
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


def extract_infobox_v2(infobox_html: bs4.element.Tag):
    """
    Extract an infobox of type V2 (https://fr.wikipedia.org/wiki/Projet:Infobox/V2)
    """
    tbody = infobox_html.find("tbody")
    data, images = [], set()
    for tr in tbody:
        row = _parse_tr(tr)
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


def extract_infobox_v3(infobox_html: bs4.element.Tag):
    """
    Extract an infobox of type V3 (https://fr.wikipedia.org/wiki/Projet:Infobox/V3).
    """
    title, images, data = "", set(), []
    for tag in infobox_html:
        tag: bs4.element.Tag
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
                    row = _parse_tr(tr)
                    if row:
                        data.append(row)

            else:
                logger.error("Table without tbody")
        else:
            if isinstance(tag, bs4.element.Tag) and tag.text:
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
    raise NotImplementedError


def extract_table(html_table: bs4.element.Tag):
    """
    Extract a classical HTML table.
    """
    html_caption = html_table.find("caption")
    title = html_caption.text if html_caption else ""
    data = []
    tbody = html_table.find("tbody")
    for tr in tbody:
        row = _parse_tr(tr)
        if row:
            data.append(row)

    return {"title": title, "data": data, "type": "table"}


def extract(table: bs4.element.Tag):
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
        return extract_infobox_v3(table)

    elif table_type == "infobox_v2":
        return extract_infobox_v2(table)

    elif table_type == "infobox":
        return extract_infobox(table)

    elif table_type == "table":
        return extract_table(table)

    else:
        raise ValueError(
            f'Unknown extraction type {table_type}. Extraction type should be one of ["infobox_v3", "infobox_v2", "infobox", "table"] '
        )
