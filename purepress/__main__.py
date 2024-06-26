import os
import re
import shutil
import functools
import traceback
from pathlib import Path
from urllib.parse import urlparse
from contextlib import contextmanager

import click
from flask import url_for

from .__meta__ import __version__
from . import app, load_posts, raw_folder, root_folder, pages_folder, posts_folder, static_folder, theme_static_folder

echo = click.echo
echo_green = functools.partial(click.secho, fg="green")
echo_red = functools.partial(click.secho, fg="red")
echo_yellow = functools.partial(click.secho, fg="yellow")


@contextmanager
def step(op_name: str):
    echo(f"{op_name}...", nl=False)
    yield
    echo_green("OK")


@click.group(name="purepress", short_help="A simple static blog generator.")
@click.version_option(version=__version__)
def cli():
    pass


DEFAULT_PUREPRESS_TOML = """\
[site]
title = "My Blog"
subtitle = "Here is my blog"
author = "My Name"
timezone = "Asia/Shanghai"

[config]
posts_per_index_page = 5
"""

DEFAULT_POST_TEMPLATE = """\
---
title: A demo {0}
---

This is a demo {0}.
"""


@cli.command("init", short_help="Initialize an instance.")
def init_command():
    if root_folder.glob("*"):
        echo_red(f'The instance folder "{root_folder}" is not empty')
        exit(1)
    with step("Creating folders"):
        posts_folder.mkdir(parents=True, exist_ok=True)
        pages_folder.mkdir(parents=True, exist_ok=True)
        static_folder.mkdir(parents=True, exist_ok=True)
        raw_folder.mkdir(parents=True, exist_ok=True)
    with step("Creating default purepress.toml"):
        with open(root_folder / "purepress.toml", mode="w", encoding="utf-8") as f:
            f.write(DEFAULT_PUREPRESS_TOML)
    with step("Createing demo page"):
        with open(pages_folder / "demo.md", mode="w", encoding="utf-8") as f:
            f.write(DEFAULT_POST_TEMPLATE.format("page"))
    with step("Createing demo post"):
        with open(posts_folder / "1970-01-01-demo.md", mode="w", encoding="utf-8") as f:
            f.write(DEFAULT_POST_TEMPLATE.format("post"))
    echo_green("OK! Now you can install a theme and preview the site.")


@cli.command("preview", short_help="Preview the site.")
@click.option("--host", "-h", default="127.0.0.1", help="Host to preview the site.")
@click.option("--port", "-p", default=8080, help="Port to preview the site.")
@click.option("--no-debug", is_flag=True, default=False, help="Do not preview in debug mode.")
def preview_command(host, port, no_debug):
    app.config["ENV"] = "development"
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.run(host=host, port=port, debug=not no_debug, use_reloader=False)


@cli.command("build", short_help="Build the site.")
@click.option(
    "--url-root",
    prompt="Please enter the url root (used as prefix of generated url)",
    help='The url root of your site, e.g. "http://example.com/blog/".',
)
def build_command(url_root):
    res = urlparse(url_root)
    app_root = res.path or "/"
    app.config["PREFERRED_URL_SCHEME"] = res.scheme or "http"
    app.config["SERVER_NAME"] = res.netloc or "localhost"
    if not res.netloc:
        echo_yellow('The url root does not contain a valid server name, "localhost" will be used.')
    app.config["APPLICATION_ROOT"] = app_root
    # mark as 'BUILDING' status, so that templates can react properly,
    app.config["BUILDING"] = True

    try:
        with app.test_client() as client:
            build(lambda url: client.get(re.sub(r"^" + app_root, "/", url)))
        echo_green('OK! Now you can find the built site in the "build" folder.')
    except Exception:
        traceback.print_exc()
        echo_red("Failed to build the site.")
        exit(1)


def build(get):
    # prepare folder paths
    build_folder = root_folder / "build"
    build_static_folder = build_folder / "static"
    build_static_theme_folder = build_static_folder / "theme"
    build_pages_folder = build_folder
    build_posts_folder = build_folder / "post"
    build_categories_folder = build_folder / "category"
    build_tags_folder = build_folder / "tag"
    build_archive_folder = build_folder / "archive"
    build_index_page_folder = build_folder / "page"

    with step("Creating build folder"):
        if os.path.isdir(build_folder):
            shutil.rmtree(build_folder)
        elif os.path.exists(build_folder):
            os.remove(build_folder)
        os.mkdir(build_folder)

    with step("Copying raw files"):
        copy_folder_content(raw_folder, build_folder)

    with step("Copying theme static files"):
        os.makedirs(build_static_theme_folder, exist_ok=True)
        copy_folder_content(theme_static_folder, build_static_theme_folder)

    with step("Copying static files"):
        copy_folder_content(static_folder, build_static_folder)

    with step("Building custom pages"):
        for dirname, _, files in os.walk(pages_folder):
            if os.path.basename(dirname).startswith("."):
                continue
            rel_dirname = os.path.relpath(dirname, pages_folder)
            (build_pages_folder / rel_dirname).mkdir(parents=True, exist_ok=True)
            for file in filter(lambda f: not f.startswith("."), files):
                rel_path = Path(rel_dirname) / file
                dst_rel_path = rel_path.with_suffix(".html")
                dst_path = build_pages_folder / dst_rel_path
                rel_url = dst_rel_path.as_posix()
                with app.test_request_context():
                    url = url_for("page", rel_url=rel_url)
                res = get(url)
                with open(dst_path, "wb") as f:
                    f.write(res.data)

    with app.test_request_context():
        posts = load_posts(meta_only=True)
    with step("Building posts"):
        for post in posts:
            filename = post["filename"]
            year, month, day, name = Path(filename).stem.split("-", maxsplit=3)
            dst_dir = build_posts_folder / year / month / day / name
            dst_dir.mkdir(parents=True, exist_ok=True)
            dst_path = dst_dir / "index.html"
            with app.test_request_context():
                url = url_for("post", year=year, month=month, day=day, name=name)
            res = get(url)
            with open(dst_path, "wb") as f:
                f.write(res.data)

    with step("Building categories"):
        categories = set(functools.reduce(lambda c, p: c + p.get("categories", []), posts, []))
        for category in categories:
            category_folder = build_categories_folder / category
            os.makedirs(category_folder, exist_ok=True)
            with app.test_request_context():
                url = url_for("category", name=category)
            res = get(url)
            with open(category_folder / "index.html", "wb") as f:
                f.write(res.data)

    with step("Building tags"):
        tags = set(functools.reduce(lambda t, p: t + p.get("tags", []), posts, []))
        for tag in tags:
            tag_folder = build_tags_folder / tag
            os.makedirs(tag_folder, exist_ok=True)
            with app.test_request_context():
                url = url_for("tag", name=tag)
            res = get(url)
            with open(tag_folder / "index.html", "wb") as f:
                f.write(res.data)

    with step("Building archive"):
        os.makedirs(build_archive_folder, exist_ok=True)
        with app.test_request_context():
            url = url_for("archive")
        res = get(url)
        with open(build_archive_folder / "index.html", "wb") as f:
            f.write(res.data)

    with step("Building index"):
        with app.test_request_context():
            url = url_for("index")
        res = get(url)
        with open(build_folder / "index.html", "wb") as f:
            f.write(res.data)
        page_num = 2
        while True:
            page_folder = build_index_page_folder / str(page_num)
            os.makedirs(page_folder, exist_ok=True)
            with app.test_request_context():
                url = url_for("index_page", page_num=page_num)
            res = get(url)
            if res.status_code != 200:
                break
            with open(page_folder / "index.html", "wb") as f:
                f.write(res.data)
            page_num += 1

    with step("Building feed"):
        with app.test_request_context():
            url = url_for("feed")
        res = get(url)
        with open(build_folder / "feed.xml", "wb") as f:
            f.write(res.data)

    with step("Building 404"):
        with app.test_request_context():
            url = url_for("page_not_found")
        res = get(url)
        with open(build_folder / "404.html", "wb") as f:
            f.write(res.data)


def copy_folder_content(src: Path, dst: Path):
    """
    Copy all content in src directory to dst directory.
    The src and dst must exist.
    """
    if not src.is_dir():
        return
    for item in src.iterdir():
        if item.is_file():
            shutil.copy2(item, dst / item.name)
        elif item.is_dir():
            shutil.copytree(item, dst / item.name)
