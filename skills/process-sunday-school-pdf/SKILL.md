---
name: process-sunday-school-pdf
description: Convert Intermediate or Senior Sunday School stage PDFs into individual Markdown lessons, a linked stage index, and extracted graphic pages.
---

# Process Sunday School PDFs

Use for the Intermediate (ages 13-14) and Senior (ages 15 and over) five-stage notes. Derive lesson counts, titles, page boundaries, and graphics from each new source rather than assuming another book's lesson sequence or page numbers.

## Deliverables

In the user's output directory, create:

- `intermediate_{stage}_lessons/Lesson 01 - {Title}.md`, one file per lesson, numbered with two digits in filenames.
- `intermediate_{stage}_graphics/page-001.png`, full graphic pages rendered at 150 dpi, numbered by physical PDF page (1-based).
- `{Book Title} - Lessons.md`, a stage index with links to the individual lesson files, source PDF, course graphics, and foreword when present. Do not include lesson bodies in the index. If that index filename belongs to another stage, choose a stage-qualified filename.

For Senior books, set `folder_prefix: "senior"`, `level: "Senior"`, and `ages: "15 and over"` in the plan. This produces `senior_{stage}_lessons/` and `senior_{stage}_graphics/`. Use `Senior Stage {stage} - {Book Title} - Lessons.md` for the index to avoid collisions with Intermediate books. Omitted fields retain the original Intermediate defaults. Treat the two levels as independent source material.

Keep graphics and lessons in sibling folders, with relative, URL-encoded links so the set remains portable. The original PDF stays intact. Preserve teaching notes, Scripture references, applications, reference libraries, paragraph questions, and essay questions. This is a conversion, not a summary or newly authored lesson. Retain the source's theological perspective and historical context; correct clear OCR errors against the scan without silently revising teachings or modernizing dated claims.

## Efficient workflow

1. Inspect existing files and local instructions. Locate the bundled Python and Poppler through `load_workspace_dependencies` when available; do not assume the system Python has PDF libraries. Use the available PDF skill for PDF inspection. The helper needs `pdfplumber`, Pillow, and `pdftoppm`; it uses no network service.
2. Run `scripts/stage_pdf.py prepare SOURCE.pdf WORKDIR --pdftoppm PATH`. This extracts text and line coordinates once to `pages.json`, writes a readable `source.txt`, and renders numbered contact sheets at low resolution. Reuse these files during subsequent edits instead of repeatedly parsing or dumping the entire PDF into chat. Inspect every contact sheet and read the source text by lesson-sized ranges.
3. Create `WORKDIR/plan.json` using the schema below. Identify all lesson starts from the actual table of contents and body headings. Classify every PDF page as lesson text, index text, graphics, or ignored with a reason. A mixed text/illustration page belongs to both lesson text and graphics. Link graphics by subject, not just adjacency or a map's lesson numbers. A graphic can serve multiple lessons. Retain captions within the full-page PNG; avoid duplicating map OCR as lesson prose. Blank pages need no image.
4. Run `scripts/stage_pdf.py build WORKDIR/plan.json OUTPUTDIR --pdftoppm PATH`. It uses cached text, creates the separate lessons and index directly, renders only selected graphic pages, and verifies links. Existing output files are protected; use `--overwrite` only after inspecting them and confirming they are this task's generated outputs. Do not overwrite unrelated stages.
5. Review and edit the generated Markdown against the source. The paragraph/heading formatter is heuristic, not a substitute for reading. Repair split headings, paragraphs continued across page boundaries, Scripture citations, question numbering, and lists. Reconstruct multi-column tables as Markdown tables from the scan; never accept interleaved table OCR. For substantial layout exceptions, use a reviewed page override in the plan and rebuild before making final manual edits. OCR image-only text pages with available local tools if necessary; do not treat empty extraction as proof of a graphic-only page.
6. Inspect the final PNGs for legibility, completeness, and correct orientation. Run `scripts/stage_pdf.py validate WORKDIR/plan.json OUTPUTDIR` after final edits. Confirm every lesson is represented, questions and reference sections remain, and all source/graphic/lesson links resolve. Report counts and the index link. Commit only when requested.

Keep preparation data and the plan in a task-specific temporary directory. Keep it through review so correction is cheap; do not ship contact sheets or extraction caches as lesson assets. Do not reprocess Stage 4 when asked to process another stage.

## Plan format

Paths below are relative to `plan.json`. Physical PDF pages are always 1-based; do not substitute printed page labels. Expand page lists explicitly, including mixed graphic/text pages where the text must be preserved.

```json
{
  "source": "../../source.pdf",
  "stage": 1,
  "title": "Book title from the PDF",
  "publisher": "Christadelphian Sunday School Association",
  "index_filename": "Book title from the PDF - Lessons.md",
  "index_pages": [3],
  "ignored_pages": {"2": "Blank", "4": "Original contents replaced by linked index"},
  "lessons": [
    {"number": 1, "title": "First lesson title", "pages": [5, 6, 7]}
  ],
  "graphics": [
    {"page": 1, "label": "Cover", "lessons": [], "course": true},
    {"page": 8, "label": "Map for the first lesson", "lessons": [1], "course": false}
  ],
  "overrides": {"6": "reviewed-page-006.md"}
}
```

The example is schematic; inventory validation rejects an incomplete classification. `overrides` replaces a whole page's extracted text with reviewed Markdown. Include source page markers in the output; do not copy the lesson's main title into an override. `index_pages` supplies foreword/front-matter text only, not lesson content. Empty `lessons` on a graphic means course-wide material and requires `course: true`. Numbers must be consecutive from 1; expected lesson count comes from the source, not this example.
