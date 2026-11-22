"""Cache PDF inspection, build reviewed stage plans, and validate local links."""
import argparse
import json
import os
import re
import subprocess
import statistics
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def render(pdf, page, prefix, dpi, binary):
    subprocess.run([binary, "-f", str(page), "-l", str(page), "-r", str(dpi),
                    "-singlefile", "-png", str(pdf), str(prefix)], check=True,
                   capture_output=True)


def prepare(args):
    import pdfplumber
    from PIL import Image, ImageDraw
    work = Path(args.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    cache = work / "pages.json"
    if cache.exists():
        raise ValueError("Preparation already exists; reuse it or choose a fresh work directory.")
    pdf = Path(args.source).resolve(strict=True)
    pages = []
    with pdfplumber.open(pdf) as doc:
        for n, page in enumerate(doc.pages, 1):
            lines = [{k: line[k] for k in ("text", "x0", "top", "bottom")}
                     for line in page.extract_text_lines()]
            pages.append({"number": n, "height": page.height, "lines": lines})
            page.close()
    cache.write_text(json.dumps({"source": str(pdf), "pages": pages},
                               ensure_ascii=False), encoding="utf-8")
    (work / "source.txt").write_text("\n\n".join(
        f"--- PDF PAGE {p['number']} ---\n" + "\n".join(x["text"] for x in p["lines"])
        for p in pages), encoding="utf-8")
    subprocess.run([args.pdftoppm, "-r", "30", "-png", str(pdf), str(work / "thumb")],
                   check=True, capture_output=True)
    for start in range(0, len(pages), 24):
        canvas = Image.new("RGB", (1000, 1500), "white")
        draw = ImageDraw.Draw(canvas)
        for j, n in enumerate(range(start + 1, min(start + 25, len(pages) + 1))):
            matches = list(work.glob(f"thumb-{'0' * (len(str(len(pages))) - len(str(n)))}{n}.png"))
            if not matches:
                matches = [p for p in work.glob("thumb-*.png") if int(p.stem.split("-")[-1]) == n]
            with Image.open(matches[0]) as image:
                image.thumbnail((240, 220))
                x, y = j % 4 * 250, j // 4 * 250
                canvas.paste(image, (x, y + 22))
                draw.text((x + 5, y + 4), f"PDF page {n}", fill="red")
        canvas.save(work / f"contact-{start // 24 + 1:02d}.png")
    print(f"Prepared {len(pages)} pages in {work}")


def load_plan(path):
    path = Path(path).resolve()
    plan = read_json(path)
    cache = read_json(path.parent / "pages.json")
    source = (path.parent / plan["source"]).resolve(strict=True)
    if source != Path(cache["source"]).resolve():
        raise ValueError("Plan source differs from prepared source.")
    if plan["stage"] not in range(1, 6):
        raise ValueError("Stage must be 1-5.")
    lessons = plan["lessons"]
    numbers = [x["number"] for x in lessons]
    if not lessons or numbers != list(range(1, len(lessons) + 1)):
        raise ValueError("Lesson numbers must be consecutive from 1.")
    known = set(range(1, len(cache["pages"]) + 1))
    classified = set(plan.get("index_pages", []))
    ignored = plan.get("ignored_pages", {})
    if any(not reason.strip() for reason in ignored.values()):
        raise ValueError("Ignored pages require reasons.")
    classified.update(map(int, ignored))
    assigned = set()
    for lesson in lessons:
        if not lesson["pages"] or len(set(lesson["pages"])) != len(lesson["pages"]):
            raise ValueError("Lessons need unique text pages.")
        if assigned.intersection(lesson["pages"]):
            raise ValueError("Text page assigned to multiple lessons; use an override to split deliberately.")
        assigned.update(lesson["pages"])
    classified.update(assigned)
    seen_graphics = set()
    for graphic in plan.get("graphics", []):
        page = graphic["page"]
        if page in seen_graphics:
            raise ValueError("Duplicate graphic page.")
        seen_graphics.add(page)
        if not set(graphic["lessons"]).issubset(numbers):
            raise ValueError("Graphic refers to an unknown lesson.")
        if not graphic["lessons"] and not graphic.get("course"):
            raise ValueError("Graphic has no lesson or course placement.")
    classified.update(seen_graphics)
    if classified != known:
        raise ValueError(f"Unclassified pages: {sorted(known-classified)}; invalid pages: {sorted(classified-known)}")
    if set(map(int, ignored)).intersection(assigned | seen_graphics | set(plan.get("index_pages", []))):
        raise ValueError("Ignored pages are also used.")
    if set(plan.get("index_pages", [])).intersection(assigned):
        raise ValueError("Index cannot contain lesson bodies.")
    if not set(map(int, plan.get("overrides", {}))).issubset(known):
        raise ValueError("Invalid override page.")
    return path, plan, cache, source


def page_markdown(page, first=False):
    """Heuristic paragraph reflow; visually review tables and titles afterward."""
    lines = [x for x in page["lines"] if not (
        re.fullmatch(r"\d{1,3}", x["text"].strip()) and x["top"] > page["height"] * .9)]
    if first and lines and re.match(r"^\d+[.,]\s", lines[0]["text"]):
        lines = lines[1:]
    base = min((x["x0"] for x in lines), default=0)
    pitches = [b["top"] - a["top"] for a, b in zip(lines, lines[1:])
               if 3 < b["top"] - a["top"] < 25]
    paragraph_pitch = statistics.median(pitches) * 1.45 if pitches else 14
    result, buffer, prev = [], "", None

    def flush():
        nonlocal buffer
        if buffer:
            result.append(buffer.strip())
            buffer = ""

    for line in lines:
        text = line["text"].strip()
        prefix = text.split("(", 1)[0].strip()
        heading = len(prefix) > 5 and prefix.isupper() and len(text) < 180
        if heading:
            flush()
            result.append("### " + text.rstrip(":"))
        else:
            if prev and (line["top"] - prev["top"] > paragraph_pitch or
                         (6 < line["x0"] - base < 22 and not re.match(r"^(?:\d+[.]|[-•])\s", buffer)) or
                         re.match(r"^(?:\d+[.]|[-•])\s", text)):
                flush()
            if text.startswith("•"):
                text = "- " + text[1:].lstrip()
            if buffer.endswith("-"):
                buffer = buffer[:-1] + text
            else:
                buffer += (" " if buffer else "") + text
        prev = line
    flush()
    return "\n\n".join(result)


def filename(lesson):
    title = re.sub(r'[<>:"/\\|?*#^\[\]\x00-\x1f]', " -", lesson["title"])
    title = re.sub(r"\s+", " ", title).strip(" .")
    return f"Lesson {lesson['number']:02d} - {title}.md"


def link_name(path):
    """Name Obsidian matches for a bare link: Markdown files drop `.md`."""
    path = Path(path)
    return (path.stem if path.suffix.lower() == ".md" else path.name).casefold()


def find_vault(start):
    """Nearest folder at or above `start` that contains `.obsidian/`, else None."""
    start = Path(start).resolve()
    for folder in [start, *start.parents]:
        if (folder / ".obsidian").is_dir():
            return folder
    return None


def vault_files(vault):
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            yield Path(root, name).resolve()


MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
WIKILINK = re.compile(r"!?\[\[([^\]]+)\]\]")


class Linker:
    """Writes and resolves local links in the one style the output location calls for.

    No `.obsidian/` above the output: relative, URL-encoded Markdown links.
    Inside an Obsidian vault: follow `.obsidian/app.json` exactly as Obsidian would.
    `useMarkdownLinks` false/absent -> wikilinks; true -> Markdown links.
    `newLinkFormat` "shortest" (default) -> bare name when unique in the vault, else
    vault-root path; "absolute" -> vault-root path; "relative" -> path from the note.
    """

    def __init__(self, out, planned=()):
        self.vault = find_vault(out)
        settings = {}
        if self.vault and (self.vault / ".obsidian" / "app.json").is_file():
            settings = read_json(self.vault / ".obsidian" / "app.json")
        self.wiki = bool(self.vault) and not settings.get("useMarkdownLinks", False)
        self.format = settings.get("newLinkFormat", "shortest") if self.vault else "relative"
        if self.format not in ("shortest", "absolute", "relative"):
            raise ValueError(f"Unsupported Obsidian newLinkFormat: {self.format}")
        self.by_name = {}
        if self.vault:
            for p in {*vault_files(self.vault), *(Path(x).resolve() for x in planned)}:
                self.by_name.setdefault(link_name(p), set()).add(p)

    def describe(self):
        if not self.vault:
            return "relative Markdown links (no Obsidian vault found)"
        kind = "wikilinks" if self.wiki else "Markdown links"
        return f"Obsidian {kind}, {self.format} paths (vault: {self.vault})"

    def link(self, label, target, parent):
        target = Path(target).resolve()
        if not self.vault:
            relative = Path(os.path.relpath(target, parent)).as_posix()
            return f"[{label}]({quote(relative, safe='/')})"
        try:
            from_root = target.relative_to(self.vault).as_posix()
        except ValueError:
            raise ValueError(f"{target} is outside the Obsidian vault {self.vault}; copy it into "
                             "the vault (normally the output folder) and point the plan at the copy.")
        if self.format == "absolute":
            path = from_root
        elif self.format == "relative":
            path = Path(os.path.relpath(target, parent)).as_posix()
            if self.wiki and not path.startswith("../"):
                path = "./" + path
        else:
            path = target.name if len(self.by_name.get(link_name(target), ())) == 1 else from_root
        if not self.wiki:
            return f"[{label}]({quote(path, safe='/')})"
        if any(c in label for c in "[]|"):
            raise ValueError(f"Link label cannot contain [, ] or | in a wikilink: {label}")
        if path.lower().endswith(".md"):
            path = path[:-3]
        return f"[[{path}]]" if label == path.rsplit("/", 1)[-1] else f"[[{path}|{label}]]"

    def links(self, text, source):
        """Resolve every local link in `text`; raise on a broken, ambiguous or off-style link."""
        found = []
        markdown = [m.group(1).strip("<>") for m in MARKDOWN_LINK.finditer(text)]
        markdown = [unquote(urlsplit(t).path) for t in markdown if not urlsplit(t).scheme and urlsplit(t).path]
        wiki = [re.split(r"\\?\|", m.group(1))[0].split("#")[0] for m in WIKILINK.finditer(text)]
        if self.wiki and markdown:
            raise ValueError(f"Markdown link in {source}; this vault uses wikilinks: {markdown[0]}")
        if not self.wiki and wiki:
            raise ValueError(f"Wikilink in {source}; this location uses Markdown links: [[{wiki[0]}]]")
        found += [self.resolve(t, source, wiki=False) for t in markdown]
        found += [self.resolve(t, source, wiki=True) for t in wiki]
        return found

    def resolve(self, t, source, wiki):
        if wiki and self.vault and "/" not in t:
            matches = self.by_name.get(link_name(t + ".md"), set())
            if len(matches) != 1:
                kind = "Ambiguous" if matches else "Broken"
                raise ValueError(f"{kind} link in {source}: [[{t}]] matches {len(matches)} files")
            return next(iter(matches))
        bases = [source.parent]
        if self.vault and not t.startswith(("./", "../")):
            bases.append(self.vault)
        names = [t, t + ".md"] if wiki else [t]
        for base in bases:
            for name in names:
                if (base / name).is_file():
                    return (base / name).resolve()
        if self.vault and "/" not in t:
            matches = self.by_name.get(link_name(t), set())
            if len(matches) == 1:
                return next(iter(matches))
            if matches:
                raise ValueError(f"Ambiguous link in {source}: {t} matches {len(matches)} files")
        raise ValueError(f"Broken link in {source}: {t}")


def outputs(plan, out):
    stage = plan["stage"]
    name = plan.get("index_filename", f"{plan['title']} - Lessons.md")
    if Path(name).name != name or not name.endswith(".md"):
        raise ValueError("index_filename must be a Markdown basename.")
    prefix = plan.get("folder_prefix", "intermediate")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", prefix):
        raise ValueError("folder_prefix must be a simple lowercase folder prefix.")
    return (out / name, out / f"{prefix}_{stage}_lessons",
            out / f"{prefix}_{stage}_graphics")


def build(args):
    path, plan, cache, source = load_plan(args.plan)
    out = Path(args.output).resolve()
    index, lessons_dir, graphics_dir = outputs(plan, out)
    targets = [index, *[lessons_dir / filename(x) for x in plan["lessons"]],
               *[graphics_dir / f"page-{x['page']:03d}.png" for x in plan.get("graphics", [])]]
    if len(set(targets)) != len(targets):
        raise ValueError("Output filename collision.")
    if not args.overwrite and any(x.exists() for x in targets):
        raise ValueError("Output exists; review it before using --overwrite.")
    linker = Linker(out, targets)
    local_link = linker.link
    local_link("Original PDF", source, out)  # fail early if the source is outside a vault
    lessons_dir.mkdir(parents=True, exist_ok=True)
    graphics_dir.mkdir(parents=True, exist_ok=True)
    for graphic in plan.get("graphics", []):
        render(source, graphic["page"], graphics_dir / f"page-{graphic['page']:03d}", 150, args.pdftoppm)

    def graphic_link(graphic, parent):
        n = graphic["page"]
        return local_link(f"{graphic['label']} (PDF page {n})", graphics_dir / f"page-{n:03d}.png", parent)

    def text_for(n, first=False):
        override = plan.get("overrides", {}).get(str(n))
        text = ((path.parent / override).read_text(encoding="utf-8") if override
                else page_markdown(cache["pages"][n-1], first))
        if not text.strip():
            raise ValueError(f"PDF page {n} assigned as text but extraction is empty; inspect/OCR or reclassify.")
        return f"<!-- PDF page {n} -->\n\n{text.strip()}"

    publisher = plan.get("publisher", "Christadelphian Sunday School Association")
    for lesson in plan["lessons"]:
        n = lesson["number"]
        blocks = [f"# Lesson {n}: {lesson['title']}",
                  f"**{plan['title']} - Stage {plan['stage']} of 5 | Ages {plan.get('ages', '13-14')}**",
                  f"Source: {publisher}. Converted from the source PDF; some scan/OCR errors may remain. Page references use PDF page numbers.",
                  local_link("Original PDF", source, lessons_dir),
                  "*Source: PDF pages " + ", ".join(map(str, lesson["pages"])) + ".*"]
        graphics = [g for g in plan.get("graphics", []) if n in g["lessons"]]
        if graphics:
            blocks += ["**Related graphics**", "\n".join("- " + graphic_link(g, lessons_dir) for g in graphics)]
        blocks += [text_for(p, j == 0) for j, p in enumerate(lesson["pages"])]
        (lessons_dir / filename(lesson)).write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    blocks = [f"# {plan['title']}",
              f"**Stage {plan['stage']} of 5 - {plan.get('level', 'Intermediate')} Sunday School notes, ages {plan.get('ages', '13-14')}**",
              f"Source: {publisher}. This index links to individual lesson files containing teaching notes, applications, reference libraries, and review questions. Page references use physical PDF page numbers.",
              local_link("Original PDF", source, out)]
    course = [g for g in plan.get("graphics", []) if g.get("course")]
    if course:
        blocks += ["## Course graphics", "\n\n".join(graphic_link(g, out) for g in course)]
    blocks += ["## Contents", "\n".join("- " + local_link(
        f"Lesson {x['number']}: {x['title']}", lessons_dir / filename(x), out) for x in plan["lessons"])]
    if plan.get("index_pages"):
        blocks += ["## Foreword and introductory notes", *[text_for(n) for n in plan["index_pages"]]]
    index.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    validate(args)


def validate(args):
    from PIL import Image
    _, plan, _, _ = load_plan(args.plan)
    out = Path(args.output).resolve()
    index, lessons_dir, graphics_dir = outputs(plan, out)
    expected = {filename(x) for x in plan["lessons"]}
    if {x.name for x in lessons_dir.glob("*.md")} != expected:
        raise ValueError("Lesson file inventory differs from plan.")
    if {x.name for x in graphics_dir.glob("*.png")} != {f"page-{g['page']:03d}.png" for g in plan.get("graphics", [])}:
        raise ValueError("Graphics inventory differs from plan.")
    linker = Linker(out)
    count = 0
    resolved = {}
    for p in [index, *[lessons_dir / filename(x) for x in plan["lessons"]]]:
        text = p.read_text(encoding="utf-8")
        if "\ufffd" in text:
            raise ValueError(f"Unresolved replacement glyph in {p}")
        if p == index and re.search(r"^#{1,3} Lesson \d+:", text, re.M):
            raise ValueError("Index contains lesson bodies.")
        if p != index and len(re.findall(r"^# Lesson \d+:", text, re.M)) != 1:
            raise ValueError(f"Expected one lesson heading in {p}")
        resolved[p] = set(linker.links(text, p))
        count += len(resolved[p])
    for lesson in plan["lessons"]:
        content = (lessons_dir / filename(lesson)).read_text(encoding="utf-8")
        for n in lesson["pages"]:
            if f"<!-- PDF page {n} -->" not in content:
                raise ValueError(f"Missing text page {n}")
    for lesson in plan["lessons"]:
        if (lessons_dir / filename(lesson)).resolve() not in resolved[index]:
            raise ValueError(f"Lesson missing from index links: {filename(lesson)}")
    for graphic in plan.get("graphics", []):
        png = graphics_dir / f"page-{graphic['page']:03d}.png"
        with Image.open(png) as image:
            image.verify()
        for n in graphic["lessons"]:
            lesson_file = lessons_dir / filename(plan["lessons"][n-1])
            if png.resolve() not in resolved[lesson_file]:
                raise ValueError(f"Graphic {png.name} missing from lesson {n}.")
        if graphic.get("course") and png.resolve() not in resolved[index]:
            raise ValueError(f"Course graphic {png.name} missing from index.")
    print(f"Link style: {linker.describe()}")
    print(f"Validated {len(expected)} lessons, {len(plan.get('graphics', []))} graphics, {count} local links.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("source")
    prep.add_argument("work")
    prep.add_argument("--pdftoppm", default="pdftoppm")
    for name in ("build", "validate"):
        command = commands.add_parser(name)
        command.add_argument("plan")
        command.add_argument("output")
        if name == "build":
            command.add_argument("--pdftoppm", default="pdftoppm")
            command.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        globals()[args.command](args)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
