"""Reads a web page for document.extract (an input of type "url"), with a guard against server-side request forgery.

- Only http and https; no user name or password in the address; at most 2000 characters.
- The host name is resolved first, and every address it resolves to must be a public one: loopback, private,
  link-local, multicast, reserved and unspecified addresses are refused (IPv4-mapped IPv6 addresses too). The
  connection then goes to the address that was checked, so a second DNS answer cannot point elsewhere.
- Redirects are followed by this code, at most MAX_REDIRECTS, and each new address is checked the same way.
- No proxy from the environment is used; each socket operation has a timeout and the whole read a deadline;
  the body is cut off above MAX_BYTES (the read fails).
- text/html becomes readable text (script, style, nav and the like are dropped), text/plain is kept, a PDF is read
  like an uploaded PDF. JavaScript is not run, so a page that builds its text in the browser gives little text.
- An RSS or Atom feed becomes a list of its items (title, date, link, summary), newest first; with max_age_days
  only the items of the last days. A feed with a DTD (<!DOCTYPE>, <!ENTITY>) is refused anywhere in it and in any
  encoding: the parser stops at the declaration, so no entity is expanded and nothing outside is loaded.
"""

from __future__ import annotations

import http.client
import ipaddress
import re
import socket
import tempfile
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import xml.parsers.expat
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from .i18n import t

TIMEOUT = 10.0          # seconds per socket operation, and the deadline of the whole read
MAX_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 3
MAX_URL = 2000
USER_AGENT = "Mehteran/1 (local document reader)"
ACCEPT = "text/html, text/plain, application/pdf, application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.9"
FEED_TYPES = {"application/rss+xml", "application/atom+xml", "application/rdf+xml", "application/xml", "text/xml"}
FEED_START = re.compile(rb"\A(\xef\xbb\xbf)?\s*(<\?xml[^>]*>\s*)?(<!--.*?-->\s*|<\?[^>]*>\s*|<!DOCTYPE[^>]*>\s*)*<(rss|feed|rdf:RDF)\b", re.S)
MAX_FEED_ITEMS = 50     # the newest items of one feed
MAX_SUMMARY = 600       # characters of an item's summary


class FetchError(Exception):
    """The page could not be read; the message is shown to the user."""


def url_problem(url: str) -> str | None:
    """Why this text is not an address Mehteran reads (None: it is one). Does not resolve the host."""
    if not isinstance(url, str) or not url or len(url) > MAX_URL or re.search(r"\s", url):
        return t("url_bad", url=str(url)[:200])
    try:
        parts = urlsplit(url)
        parts.port  # noqa: B018 - raises ValueError for a port that is not a number
    except ValueError:
        return t("url_bad", url=url[:200])
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return t("url_scheme", url=url[:200])
    if parts.username is not None or parts.password is not None:
        return t("url_credentials")
    return None


def address_allowed(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """True only for a public unicast address."""
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def checked_addresses(host: str, port: int) -> list[tuple]:
    """getaddrinfo of host, refused when one of its addresses is not public (FetchError)."""
    try:
        found = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError) as e:
        raise FetchError(t("url_dns", host=host, error=e)) from None
    if not found:
        raise FetchError(t("url_dns", host=host, error="-"))
    for *_, sockaddr in found:
        ip = ipaddress.ip_address(sockaddr[0].split("%")[0])
        if not address_allowed(ip):
            raise FetchError(t("url_private", host=host, address=str(ip)))
    return found


def _connect(address, timeout=TIMEOUT, source_address=None):
    """socket.create_connection, to the checked addresses of the host only (http.client calls this)."""
    host, port = address
    last = None
    for family, kind, proto, _, sockaddr in checked_addresses(host, port):
        sock = socket.socket(family, kind, proto)
        try:
            sock.settimeout(timeout if isinstance(timeout, (int, float)) else TIMEOUT)
            sock.connect(sockaddr)
            return sock
        except OSError as e:
            sock.close()
            last = e
    raise last or OSError("no address")


# http.client sets self._create_connection = socket.create_connection in __init__: it is replaced after that.
class _HTTP(http.client.HTTPConnection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = _connect


class _HTTPS(http.client.HTTPSConnection):  # the TLS check still uses the host name (server_hostname)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._create_connection = _connect


class _HTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(_HTTP, req)


class _HTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_HTTPS, req, context=self._context)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None  # a 3xx answer comes back as HTTPError; fetch() follows it after checking the new address


def _opener():
    # ProxyHandler({}): no proxy from the environment (a proxy would fetch any address for us).
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), _HTTPHandler(), _HTTPSHandler(), _NoRedirect())


def fetch(url: str, abort: threading.Event | None = None) -> tuple[str, str, bytes, str]:
    """(final url, media type, charset, body). FetchError with the reason when the page cannot be read."""
    deadline = time.monotonic() + TIMEOUT
    for _ in range(MAX_REDIRECTS + 1):
        problem = url_problem(url)
        if problem:
            raise FetchError(problem)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": ACCEPT})
        try:
            res = _opener().open(req, timeout=TIMEOUT)
        except urllib.error.HTTPError as e:
            with e:
                if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                    url = urljoin(url, e.headers["Location"].strip())
                    continue
                raise FetchError(t("url_status", url=url[:200], code=e.code)) from None
        except urllib.error.URLError as e:
            reason = e.reason
            if isinstance(reason, FetchError):
                raise reason from None
            raise FetchError(t("url_failed", url=url[:200], error=reason)) from None
        except FetchError:
            raise
        except (OSError, http.client.HTTPException, ValueError) as e:
            raise FetchError(t("url_failed", url=url[:200], error=e)) from None
        with res:
            length = res.headers.get("Content-Length")
            if length and length.isdigit() and int(length) > MAX_BYTES:
                raise FetchError(t("url_too_large", limit=MAX_BYTES // 1024 // 1024))
            chunks, size = [], 0
            try:
                while chunk := res.read(64 * 1024):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise FetchError(t("url_too_large", limit=MAX_BYTES // 1024 // 1024))
                    if time.monotonic() > deadline:
                        raise FetchError(t("url_timeout", seconds=int(TIMEOUT)))
                    if abort is not None and abort.is_set():
                        raise InterruptedError()
                    chunks.append(chunk)
            except InterruptedError:
                raise
            except (OSError, http.client.HTTPException) as e:
                raise FetchError(t("url_failed", url=url[:200], error=e)) from None
            media = res.headers.get_content_type()
            charset = res.headers.get_content_charset() or ""
            return res.geturl() or url, media, charset, b"".join(chunks)
    raise FetchError(t("url_redirects", count=MAX_REDIRECTS))


# --- the readable text of a page ---------------------------------------------------------------------

SKIP = {"script", "style", "nav", "noscript", "template", "svg", "iframe", "head", "form", "button", "select",
        "canvas", "object"}
BLOCK = {"p", "div", "section", "article", "main", "header", "footer", "aside", "br", "hr", "tr", "table", "ul", "ol",
         "li", "blockquote", "pre", "figure", "figcaption", "dl", "dt", "dd", "h1", "h2", "h3", "h4", "h5", "h6"}
VOID = {"br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"}


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip = 0
        self.title = ""
        self.in_title = False
        self.pre = 0

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_title = True
        if tag in SKIP and tag not in VOID:
            self.skip += 1
        if self.skip:
            return
        if tag == "pre":
            self.pre += 1
        if tag in BLOCK:
            self.out.append("\n\n" if tag not in ("br", "li", "tr", "dd", "dt") else "\n")
        if re.fullmatch(r"h[1-6]", tag):
            self.out.append("#" * int(tag[1]) + " ")
        elif tag == "li":
            self.out.append("- ")
        elif tag in ("td", "th"):
            self.out.append(" | ")

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag in SKIP and tag not in VOID:
            self.skip = max(0, self.skip - 1)
            return
        if tag == "pre":
            self.pre = max(0, self.pre - 1)
        if not self.skip and tag in BLOCK and tag not in ("li", "tr", "dd", "dt"):
            self.out.append("\n")

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        if self.skip:
            return
        self.out.append(data if self.pre else re.sub(r"\s+", " ", data))


def html_text(markup: str) -> str:
    """The readable text of an HTML page: its title as a heading, then the text of its body."""
    parser = _Text()
    parser.feed(markup)
    parser.close()
    lines = [line.strip() for line in "".join(parser.out).split("\n")]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    title = " ".join(parser.title.split())
    if title and not text.startswith(f"# {title}"):
        text = f"# {title}\n\n{text}"
    return text


def _charset(media: str, charset: str, body: bytes) -> str:
    if not charset and media == "text/html":
        found = re.search(rb"<meta[^>]+charset=[\"']?([A-Za-z0-9_-]{1,40})", body[:4096], re.I)
        charset = found.group(1).decode("ascii") if found else ""
    try:
        return body.decode(charset or "utf-8", "replace")
    except LookupError:
        return body.decode("utf-8", "replace")


# --- RSS and Atom feeds ------------------------------------------------------------------------------

def is_feed(media: str, body: bytes) -> bool:
    return media in FEED_TYPES or (media in ("text/html", "text/plain", "application/octet-stream")
                                   and FEED_START.match(body[:4096]) is not None)


def _local(tag) -> str:
    return tag.rpartition("}")[2] if isinstance(tag, str) else ""


def _child(element, *names: str):
    for child in element:
        if _local(child.tag) in names:
            return child
    return None


def _text(element, *names: str) -> str:
    found = _child(element, *names)
    return "".join(found.itertext()).strip() if found is not None else ""


def _date(value: str) -> datetime | None:
    value = value.strip()
    if not value:
        return None
    try:
        found = parsedate_to_datetime(value)  # RSS: "Fri, 14 Nov 2026 09:30:00 +0000"
    except (TypeError, ValueError, IndexError):
        try:
            found = datetime.fromisoformat(value.replace("Z", "+00:00"))  # Atom, Dublin Core: ISO 8601
        except ValueError:
            return None
    return found if found.tzinfo else found.replace(tzinfo=timezone.utc)


def _summary(raw: str) -> str:
    text = html_text(raw) if "<" in raw else raw
    text = " ".join(text.split())
    return text if len(text) <= MAX_SUMMARY else text[:MAX_SUMMARY].rsplit(" ", 1)[0] + " …"


class _Refused(Exception):
    pass


def _parse_xml(body: bytes) -> ET.Element:
    """The XML tree of body with expat, refusing any DTD (so no entity expansion, no external entity)."""
    builder = ET.TreeBuilder()
    parser = xml.parsers.expat.ParserCreate(namespace_separator="}")  # tags as "<uri>}name", like ElementTree

    def refuse(*_args):
        raise _Refused()

    parser.StartDoctypeDeclHandler = refuse
    parser.EntityDeclHandler = refuse
    parser.ExternalEntityRefHandler = refuse
    parser.StartElementHandler = builder.start
    parser.EndElementHandler = builder.end
    parser.CharacterDataHandler = builder.data
    parser.Parse(body, True)
    return builder.close()


def feed_text(body: bytes, url: str = "", max_age_days: int | None = None, now: datetime | None = None) -> str:
    """The items of an RSS (0.9x, 1.0, 2.0) or Atom feed as Markdown: the feed's title, then for each item its title,
    publication date (UTC), link and a short summary, newest first, at most MAX_FEED_ITEMS. max_age_days: only the
    items published in the last days (an item without a date is kept). FetchError when it is not a readable feed."""
    try:
        root = _parse_xml(body)
    except (_Refused, xml.parsers.expat.ExpatError, AssertionError):  # AssertionError: the builder, on broken nesting
        raise FetchError(t("feed_unreadable", url=url[:200])) from None
    kind = _local(root.tag)
    channel = _child(root, "channel") if kind in ("rss", "RDF") else root
    if kind not in ("rss", "RDF", "feed") or channel is None:
        raise FetchError(t("feed_unreadable", url=url[:200]))
    entries = [e for e in (root.iter() if kind == "RDF" else channel) if _local(e.tag) in ("item", "entry")]
    items = []
    for n, entry in enumerate(entries):
        link = _text(entry, "link")
        if kind == "feed":  # Atom: <link rel="alternate" href="..."/>
            links = [e for e in entry if _local(e.tag) == "link"]
            best = next((e for e in links if e.get("rel", "alternate") == "alternate"), links[0] if links else None)
            link = (best.get("href") or "").strip() if best is not None else ""
        if not link and _text(entry, "guid").startswith("http"):
            link = _text(entry, "guid")
        published = _date(_text(entry, "pubDate", "published", "updated", "date", "issued", "modified"))
        items.append((n, published, _text(entry, "title") or "-", urljoin(url, link) if link else "",
                      _summary(_text(entry, "description", "summary", "encoded", "content"))))
    total = len(items)
    now = now or datetime.now(timezone.utc)
    if max_age_days:
        since = now - timedelta(days=max_age_days)
        items = [i for i in items if i[1] is None or i[1] >= since]
    items.sort(key=lambda i: (i[1] is None, -(i[1].timestamp() if i[1] else 0), i[0]))
    items = items[:MAX_FEED_ITEMS]
    title = " ".join(_text(channel, "title").split()) or url
    lines = [f"# {title}", "", f"Feed: {url}" if url else "", ]
    dated = [i[1] for i in items if i[1]]
    window = f"; the last {max_age_days} days up to {now:%Y-%m-%d %H:%M} UTC" if max_age_days else ""
    span = f", published {min(dated):%Y-%m-%d} to {max(dated):%Y-%m-%d}" if dated else ""
    lines.append(f"Items: {len(items)} of {total}{span}{window}.")
    if not items:
        lines += ["", "No items in this period."]
    for _, published, item_title, link, summary in items:
        lines += ["", f"## {' '.join(item_title.split())}", "",
                  f"- Published: {published.astimezone(timezone.utc):%Y-%m-%d %H:%M} UTC" if published else "- Published: unknown"]
        if link:
            lines.append(f"- Link: {link}")
        if summary:
            lines += ["", summary]
    return "\n".join(line for n, line in enumerate(lines) if line or n == 0 or lines[n - 1]).strip()


def read_url(url: str, abort: threading.Event | None = None, read_pdf=None, max_age_days: int | None = None) -> str:
    """The text of the page at url. read_pdf(path): the text of a downloaded PDF (document.extract's reader).
    max_age_days: for a feed, only the items of the last days."""
    final, media, charset, body = fetch(url, abort)
    if is_feed(media, body):
        return feed_text(body, final, max_age_days)
    if media == "application/pdf" or (media == "application/octet-stream" and body[:5] == b"%PDF-"):
        if read_pdf is None:
            raise FetchError(t("url_type", type=media))
        with tempfile.TemporaryDirectory(prefix="mehteran-url-") as tmp:
            path = Path(tmp) / "page.pdf"
            path.write_bytes(body)
            return read_pdf(path)
    if media in ("text/html", "application/xhtml+xml"):
        return html_text(_charset("text/html", charset, body))
    if media == "text/plain" or media == "text/markdown":
        return _charset(media, charset, body).strip()
    raise FetchError(t("url_type", type=media))
