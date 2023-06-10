#!/usr/bin/env python3
from __future__ import annotations

import io
from html import escape
from typing import IO, Any

from common.formatting import FormatTree
from patchouli.book import Book, Category, Entry, Page

# extra info :(
repo_names = {
    "hexcasting": "https://raw.githubusercontent.com/gamma-delta/HexMod/main/Common/src/main/resources",
}


# TODO: type
def tag_args(kwargs: dict[str, Any]):
    return "".join(
        f" {'class' if key == 'clazz' else key.replace('_', '-')}={repr(escape(str(value)))}"
        for key, value in kwargs.items()
    )


class PairTag:
    __slots__ = ["stream", "name", "kwargs"]

    # TODO: type
    def __init__(self, stream: IO[str], name: str, **kwargs: Any):
        self.stream = stream
        self.name = name
        self.kwargs = tag_args(kwargs)

    def __enter__(self):
        print(f"<{self.name}{self.kwargs}>", file=self.stream, end="")

    def __exit__(self, _1: Any, _2: Any, _3: Any):
        print(f"</{self.name}>", file=self.stream, end="")


class Empty:
    def __enter__(self):
        pass

    def __exit__(self, _1: Any, _2: Any, _3: Any):
        pass


class Stream:
    __slots__ = ["stream"]

    def __init__(self, stream: IO[str]):
        self.stream = stream

    def tag(self, name: str, **kwargs: Any):
        keywords = tag_args(kwargs)
        print(f"<{name}{keywords} />", file=self.stream, end="")
        return self

    def pair_tag(self, name: str, **kwargs: Any):
        return PairTag(self.stream, name, **kwargs)

    def pair_tag_if(self, cond: Any, name: str, **kwargs: Any):
        return self.pair_tag(name, **kwargs) if cond else Empty()

    def empty_pair_tag(self, name: str, **kwargs: Any):
        with self.pair_tag(name, **kwargs):
            pass

    def text(self, txt: str):
        print(escape(txt), file=self.stream, end="")
        return self


# TODO: move
def get_format(out: Stream, ty: str, value: Any):
    if ty == "para":
        return out.pair_tag("p", **value)
    if ty == "color":
        return out.pair_tag("span", style=f"color: #{value}")
    if ty == "link":
        link = value
        if "://" not in link:
            link = "#" + link.replace("#", "@")
        return out.pair_tag("a", href=link)
    if ty == "tooltip":
        return out.pair_tag("span", clazz="has-tooltip", title=value)
    if ty == "cmd_click":
        return out.pair_tag(
            "span", clazz="has-cmd_click", title="When clicked, would execute: " + value
        )
    if ty == "obf":
        return out.pair_tag("span", clazz="obfuscated")
    if ty == "bold":
        return out.pair_tag("strong")
    if ty == "italic":
        return out.pair_tag("i")
    if ty == "strikethrough":
        return out.pair_tag("s")
    if ty == "underline":
        return out.pair_tag("span", style="text-decoration: underline")
    raise ValueError("Unknown format type: " + ty)


def entry_spoilered(root_info: Book, entry: Entry):
    return entry.get("advancement", None) in root_info.spoilers


def category_spoilered(root_info: Book, category: Category):
    return all(entry_spoilered(root_info, ent) for ent in category["entries"])


def write_block(out: Stream, block: FormatTree | str):
    if isinstance(block, str):
        first = False
        for line in block.split("\n"):
            if first:
                out.tag("br")
            first = True
            out.text(line)
        return
    sty_type = block.style.type
    if sty_type == "base":
        for child in block.children:
            write_block(out, child)
        return
    tag = get_format(out, sty_type, block.style.value)
    with tag:
        for child in block.children:
            write_block(out, child)


def anchor_toc(out: Stream):
    with out.pair_tag(
        "a", href="#table-of-contents", clazz="permalink small", title="Jump to top"
    ):
        out.empty_pair_tag("i", clazz="bi bi-box-arrow-up")


def permalink(out: Stream, link: str):
    with out.pair_tag("a", href=link, clazz="permalink small", title="Permalink"):
        out.empty_pair_tag("i", clazz="bi bi-link-45deg")


def write_page(out: Stream, pageid: str, page: Page):
    if anchor := page.get("anchor"):
        anchor_id = pageid + "@" + anchor
    else:
        anchor_id = None

    with out.pair_tag_if(anchor_id, "div", id=anchor_id):
        if "header" in page or "title" in page:
            with out.pair_tag("h4"):
                out.text(page.get("header", page.get("title", None)))
                if anchor_id:
                    permalink(out, "#" + anchor_id)

        ty = page["type"]
        if ty == "patchouli:text":
            write_block(out, page["text"])
        elif ty == "patchouli:empty":
            pass
        elif ty == "patchouli:link":
            write_block(out, page["text"])
            with out.pair_tag("h4", clazz="linkout"):
                with out.pair_tag("a", href=page["url"]):
                    out.text(page["link_text"])
        elif ty == "patchouli:spotlight":
            with out.pair_tag("h4", clazz="spotlight-title page-header"):
                out.text(page["item_name"])
            if "text" in page:
                write_block(out, page["text"])
        elif ty == "patchouli:crafting":
            with out.pair_tag("blockquote", clazz="crafting-info"):
                out.text(f"Depicted in the book: The crafting recipe for the ")
                first = True
                for name in page["item_name"]:
                    if not first:
                        out.text(" and ")
                    first = False
                    with out.pair_tag("code"):
                        out.text(name)
                out.text(".")
            if "text" in page:
                write_block(out, page["text"])
        elif ty == "patchouli:image":
            with out.pair_tag("p", clazz="img-wrapper"):
                for img in page["images"]:
                    modid, coords = img.split(":")
                    out.empty_pair_tag(
                        "img", src=f"{repo_names[modid]}/assets/{modid}/{coords}"
                    )
            if "text" in page:
                write_block(out, page["text"])
        elif ty == "hexcasting:crafting_multi":
            recipes = page["item_name"]
            with out.pair_tag("blockquote", clazz="crafting-info"):
                out.text(f"Depicted in the book: Several crafting recipes, for the ")
                with out.pair_tag("code"):
                    out.text(recipes[0])
                for i in recipes[1:]:
                    out.text(", ")
                    with out.pair_tag("code"):
                        out.text(i)
                out.text(".")
            if "text" in page:
                write_block(out, page["text"])
        elif ty == "hexcasting:brainsweep":
            with out.pair_tag("blockquote", clazz="crafting-info"):
                out.text(f"Depicted in the book: A mind-flaying recipe producing the ")
                with out.pair_tag("code"):
                    out.text(page["output_name"])
                out.text(".")
            if "text" in page:
                write_block(out, page["text"])
        elif ty in (
            "hexcasting:pattern",
            "hexcasting:manual_pattern_nosig",
            "hexcasting:manual_pattern",
        ):
            if "name" in page:
                with out.pair_tag("h4", clazz="pattern-title"):
                    inp = page.get("input", None) or ""
                    oup = page.get("output", None) or ""
                    pipe = f"{inp} \u2192 {oup}".strip()
                    suffix = f" ({pipe})" if inp or oup else ""
                    out.text(f"{page['name']}{suffix}")
                    if anchor_id:
                        permalink(out, "#" + anchor_id)
            with out.pair_tag("details", clazz="spell-collapsible"):
                out.empty_pair_tag("summary", clazz="collapse-spell")
                for pattern in page["op"]:
                    with out.pair_tag(
                        "canvas",
                        clazz="spell-viz",
                        width=216,
                        height=216,
                        data_string=pattern.angle_sig,
                        data_start=pattern.direction.lower(),
                        data_per_world=pattern.is_per_world,
                    ):
                        out.text(
                            "Your browser does not support visualizing patterns. Pattern code: "
                            + pattern.angle_sig
                        )
            write_block(out, page["text"])
        else:
            with out.pair_tag("p", clazz="todo-note"):
                out.text("TODO: Missing processor for type: " + ty)
            if "text" in page:
                write_block(out, page["text"])
    out.tag("br")


def write_entry(out: Stream, book: Book, entry: Entry):
    with out.pair_tag("div", id=entry["id"]):
        with out.pair_tag_if(entry_spoilered(book, entry), "div", clazz="spoilered"):
            with out.pair_tag("h3", clazz="entry-title page-header"):
                write_block(out, entry["name"])
                anchor_toc(out)
                permalink(out, "#" + entry["id"])
            for page in entry["pages"]:
                write_page(out, entry["id"], page)


def write_category(out: Stream, book: Book, category: Category):
    with out.pair_tag("section", id=category["id"]):
        with out.pair_tag_if(
            category_spoilered(book, category), "div", clazz="spoilered"
        ):
            with out.pair_tag("h2", clazz="category-title page-header"):
                write_block(out, category["name"])
                anchor_toc(out)
                permalink(out, "#" + category["id"])
            write_block(out, category["description"])
        for entry in category["entries"]:
            if entry["id"] not in book.blacklist:
                write_entry(out, book, entry)


def write_toc(out: Stream, book: Book):
    with out.pair_tag("h2", id="table-of-contents", clazz="page-header"):
        out.text("Table of Contents")
        with out.pair_tag(
            "a",
            href="javascript:void(0)",
            clazz="permalink toggle-link small",
            data_target="toc-category",
            title="Toggle all",
        ):
            out.empty_pair_tag("i", clazz="bi bi-list-nested")
        permalink(out, "#table-of-contents")
    for category in book.categories:
        with out.pair_tag("details", clazz="toc-category"):
            with out.pair_tag("summary"):
                with out.pair_tag(
                    "a",
                    href="#" + category["id"],
                    clazz="spoilered" if category_spoilered(book, category) else "",
                ):
                    out.text(category["name"])
            with out.pair_tag("ul"):
                for entry in category["entries"]:
                    with out.pair_tag("li"):
                        with out.pair_tag(
                            "a",
                            href="#" + entry["id"],
                            clazz="spoilered" if entry_spoilered(book, entry) else "",
                        ):
                            out.text(entry["name"])


def write_book(out: Stream, book: Book):
    with out.pair_tag("div", clazz="container"):
        with out.pair_tag("header", clazz="jumbotron"):
            with out.pair_tag("h1", clazz="book-title"):
                write_block(out, book.name)
            write_block(out, book.landing_text)
        with out.pair_tag("nav"):
            write_toc(out, book)
        with out.pair_tag("main", clazz="book-body"):
            for category in book.categories:
                write_category(out, book, category)


def generate_docs(book: Book, template: str) -> str:
    # FIXME: super hacky temporary solution for returning this as a string
    # just pass a string buffer to everything instead of a file
    with io.StringIO() as output:
        # TODO: refactor
        for line in template.splitlines(True):
            if line.startswith("#DO_NOT_RENDER"):
                _, *blacklist = line.split()
                book.blacklist.update(blacklist)

            if line.startswith("#SPOILER"):
                _, *spoilers = line.split()
                book.spoilers.update(spoilers)
            elif line == "#DUMP_BODY_HERE\n":
                write_book(Stream(output), book)
                print("", file=output)
            else:
                print(line, end="", file=output)

        return output.getvalue()
