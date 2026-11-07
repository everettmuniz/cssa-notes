"""Cache PDF inspection, build reviewed stage plans, and validate local links."""
import argparse
import json
import os
import re
import subprocess
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
            if prev and (line["top"] - prev["bottom"] > 5 or
                         6 < line["x0"] - base < 22 or re.match(r"^\d+[.]\s", text)):
                flush()
            if buffer.endswith("-"):
                buffer = buffer[:-1] + text
            else:
                buffer += (" " if buffer else "") + text
        prev = line
    flush()
    return "\n\n".join(result)


def filename(lesson):
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " -", lesson["title"])
    title = re.sub(r"\s+", " ", title).strip(" .")
    return f"Lesson {lesson['number']:02d} - {title}.md"


def local_link(label, target, parent):
    relative = Path(os.path.relpath(target, parent)).as_posix()
    return f"[{label}]({quote(relative, safe='/')})"


def outputs(plan, out):
    stage = plan["stage"]
    name = plan.get("index_filename", f"{plan['title']} - Lessons.md")
    if Path(name).name != name or not name.endswith(".md"):
        raise ValueError("index_filename must be a Markdown basename.")
    return (out / name, out / f"intermediate_{stage}_lessons",
            out / f"intermediate_{stage}_graphics")


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
                  f"**{plan['title']} - Stage {plan['stage']} of 5 | Ages 13-14**",
                  f"Source: {publisher}. Converted from the source PDF; some scan/OCR errors may remain. Page references use PDF page numbers.",
                  local_link("Original PDF", source, lessons_dir),
                  "*Source: PDF pages " + ", ".join(map(str, lesson["pages"])) + ".*"]
        graphics = [g for g in plan.get("graphics", []) if n in g["lessons"]]
        if graphics:
            blocks += ["**Related graphics**", "\n".join("- " + graphic_link(g, lessons_dir) for g in graphics)]
        blocks += [text_for(p, j == 0) for j, p in enumerate(lesson["pages"])]
        (lessons_dir / filename(lesson)).write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    blocks = [f"# {plan['title']}",
              f"**Stage {plan['stage']} of 5 - Intermediate Sunday School notes, ages 13-14**",
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
    count = 0
    for p in [index, *[lessons_dir / filename(x) for x in plan["lessons"]]]:
        text = p.read_text(encoding="utf-8")
        if "\ufffd" in text:
            raise ValueError(f"Unresolved replacement glyph in {p}")
        if p == index and re.search(r"^#{1,3} Lesson \d+:", text, re.M):
            raise ValueError("Index contains lesson bodies.")
        if p != index and len(re.findall(r"^# Lesson \d+:", text, re.M)) != 1:
            raise ValueError(f"Expected one lesson heading in {p}")
        for target in re.findall(r"\]\(([^)]+)\)", text):
            url = urlsplit(target.strip("<>"))
            if url.scheme or not url.path:
                continue
            if not (p.parent / unquote(url.path)).exists():
                raise ValueError(f"Broken link in {p}: {target}")
            count += 1
    for lesson in plan["lessons"]:
        content = (lessons_dir / filename(lesson)).read_text(encoding="utf-8")
        for n in lesson["pages"]:
            if f"<!-- PDF page {n} -->" not in content:
                raise ValueError(f"Missing text page {n}")
    index_text = index.read_text(encoding="utf-8")
    for lesson in plan["lessons"]:
        if quote(filename(lesson), safe="/") not in index_text:
            raise ValueError("Lesson missing from index links.")
    for graphic in plan.get("graphics", []):
        with Image.open(graphics_dir / f"page-{graphic['page']:03d}.png") as image:
            image.verify()
        for n in graphic["lessons"]:
            lesson = plan["lessons"][n-1]
            if f"page-{graphic['page']:03d}.png" not in (lessons_dir / filename(lesson)).read_text(encoding="utf-8"):
                raise ValueError("Graphic missing from intended lesson.")
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
