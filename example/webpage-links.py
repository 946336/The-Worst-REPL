#!/usr/bin/env python3

import sys

from repl import repl
from repl.base import common

import requests, re
from bs4 import BeautifulSoup

class WebpageError(common.REPLError): pass
class WebOpenFailed(WebpageError): pass

class HTMLPlayground:
    def __init__(self):
        self.url = ""
        self.soup = None
        self.links = []

    def get_webpage(self, url):
        self.url = url
        resp = requests.get(url)

        if not resp.ok:
            raise WebOpenFailed("Failed to open webpage")

        self.soup = BeautifulSoup(resp.content, features="lxml")
        return self.soup

    def extract_links(self):
        self.links = self.soup.find_all("a", href = re.compile(".*"))
        return self.links[:]

    def link_text(self):
        return [a.text for a in self.links]

    def link_destinations(self):
        dests = [a.attrs["href"] for a in self.links]

        links = []
        for dest in dests:
            if dest.startswith("/"):
                links.append(self.url + dest)
            else:
                links.append(dest)

        return links

if __name__ == "__main__":
    from repl.base.command import Command

    html = HTMLPlayground()

    def get_webpage_adaptor(url):
        try:
            html.get_webpage(url)
        except WebOpenFailed as e:
            print("HTTP GET failed for url: {}".format(url))
            return 1
        else: html.extract_links()
        return 0

    GetWebpageCommand = Command(
        get_webpage_adaptor,
        "get-webpage",
        "get-webpage url",
        "Fetch HTML from a URL"
    )

    def extract_links_adaptor():
        if html.soup: html.extract_links()
        else: print("No webpage loaded: get a webpage first")
        return 0

    ExtractLinksCommand = Command(
        extract_links_adaptor,
        "extract-links",
        "extract-links",
        "Extract links from the most recently fetched webpage"
    )

    def link_text_wrapper(n = None):
        if n is None:
            numbered_links = zip(range(1, len(html.links) + 1),
                    html.link_text())
            if html.links:
                print("\n".join(["{}: {}".format(n, t)
                    for n, t in numbered_links]))
            else: print("No links: get a webpage and extract its links first")
        else:
            n = int(n)
            if n < 1:
                print("{} is not a valid link index")
                return 2

            n -= 1
            n_expr = ["1st", "2nd", "3rd"]
            try:
                print(html.link_text()[n])
            except IndexError as e:
                print("No {} link".format(
                    n_expr[n] if n < len(n_expr) else "{}th".format(n + 1)
                ))
                return 1
            except ValueError as e:
                print("Index must be integer")
                return 1

        return 0

    LinkTextCommand = Command(
        link_text_wrapper,
        "link-text",
        "link-text [INDEX]",
        "Print the text for all links, or just the INDEXth link",
    )

    def link_destination_wrapper(n = None):
        if n is None:
            numbered_links = zip(range(1, len(html.links) + 1),
                    html.link_destinations())
            if html.links:
                print("\n".join(["{}: {}".format(n, t)
                    for n, t in numbered_links]))
            else: print("No links: get a webpage and extract its links first")
        else:
            n = int(n)
            if n < 1:
                print("{} is not a valid link index")
                return 2

            n -= 1
            n_expr = ["1st", "2nd", "3rd"]
            try:
                print(html.link_destinations()[n])
            except IndexError as e:
                print("No {} link".format(
                    n_expr[n] if n < len(n_expr) else "{}th".format(n + 1)
                ))
                return 1
            except ValueError as e:
                print("Index must be integer")
                return 1

        return 0

    LinkDestinationCommand = Command(
        link_destination_wrapper,
        "link-destination",
        "link-destination [INDEX]",
        "Print the destination URL for all links, or just the INDEXth link",
    )

    def bare_url_command(url):
        def visit(*args):
            try:
                html.get_webpage(url)
            except WebOpenFailed as e:
                print("Failed to retrieve webpage: {}".format(url))
                return 1
            else: html.extract_links()
            return 0

        return Command(
            visit,
            "no-op",
            "no-op",
            "no-op",
        )

    R = repl.REPL(application_name = "Links",
            modules_enabled = ["readline"])

    R.register(GetWebpageCommand)
    R.register(ExtractLinksCommand)
    R.register(LinkTextCommand)
    R.register(LinkDestinationCommand)

    R.set_unknown_command(bare_url_command)
    R.set_prompt(lambda _: "({}) >>> " .format(html.url) if html.url
            else "(Enter a URL) >>> ")

    R.go()

