---
name: muniz-start-intermediate-cssa-notes
description: Start the plan and notes for Everett's next Sunday School class in the sunday_school_2026-2027 repository. Creates the dated class file in the established format, with the Scripture reading, lesson reading, focus questions and draft discussion points taken from the scheduled Intermediate CSSA lesson, and adds it to the README's lesson plans list. Use when starting, scaffolding or drafting a week's class plan. Not for converting stage PDFs, transcribing recordings, or editing finished plans.
---

# Start Sunday School class notes

Create the next class plan so that Everett can start from a sound draft rather than a blank page. The plan is his teaching notes. It must sound like him, stay grounded in Scripture, and leave his decisions to him.

## Read first

- The two most recent plans in `{year}_classes/`, by date. They set the format, tone, level, stage and what was covered last week. The most recent plan takes precedence where the two differ.
- [The plan template](references/plan-template.md).
- `C:\Users\evere\.claude\voice.md`, for Everett's voice. Pay attention to its "Not his voice" and "When turning his dictated thinking into notes" sections.
- `C:\Users\evere\.claude\basf.md` when a point touches doctrine.
- The scheduled lesson file in `books/{level}_{stage}_lessons/`, read in full. Read the passages it names in the KJV as well.

## Work out what to plan

1. **Date.** Use the Sunday the user names. Otherwise use the next Sunday after today. The file is `{year}_classes/MM_DD.md` (e.g. `2026_classes/11_22.md`). Don't overwrite an existing plan. If the file exists, report it and stop unless the user asks for it to be replaced.
2. **Lesson.** Use, in order: the lesson the user names; the CSSA schedule referenced in the most recent plan's "Planning reference" (search mail only if a mail connector is available); otherwise the lesson after last week's in the same stage. If you had to fall back to the next lesson in sequence, say so plainly in your report and in the "Planning reference" section, and ask Everett to confirm it.
3. **Level and stage.** Take them from the previous plan's header unless the user says otherwise. Intermediate lessons are in `books/intermediate_{stage}_lessons/`, Senior lessons in `books/senior_{stage}_lessons/`.
4. **His own thinking.** If the user supplies dictated thoughts, a planning transcript or notes, they become the core of "Lessons for us". Keep his words and ideas. Remove filler and give them structure, but don't polish them into another style.

## Build the plan

Follow the template section by section. In particular:

- **Header.** Lesson title as `#`, then `**Sunday, {Month D, YYYY} — {Level}, Stage {n}, Lesson {n}**` and the standing aim.
- **Introduction.** Two short paragraphs. Connect last week's lesson to this one and name what to watch for in the reading. Link back to the earlier plan with a wikilink where it helps (e.g. `[[11_15#Lessons for us]]`).
- **Warm up.** Keep the standing wording and the optional "Looking back" prompt.
- **Read the Scripture around.** Start with the passages the lesson names. Extend a reading to the natural end of a section when that helps, and say why. Break it into 3–5 natural breaks with a one-line summary each. Write descriptive "what does it say?" questions in passage order, and list unfamiliar words to clarify. Add an image from `2026_classes/Images/` to a break only if one fits.
- **Read the lesson around.** Give a wikilink to the lesson (see "Links" below), `[[Lesson {NN} - {Title}|Lesson {NN} — {Title}]]`, and the collapsed Obsidian embed. Write descriptive "what does the lesson say?" questions in lesson order. Add a **Teacher's note** for any wrong reference, OCR error or claim the text doesn't support. Check every reference the lesson cites against the KJV.
- **Lessons for us.** Up to 4 numbered points. Each has: a heading that states the point; the passage to return to or a short supplementary reading; a few sentences of explanation; `**Discuss:**` with 3–5 questions that move from the text to teenagers' ordinary lives (school, friends, family, ecclesia); and `**Bring it home:**` with one concrete thing to do this week. Where a point builds on an earlier week, say so in one sentence.
- **Closing.** Keep the standing wording, plus a one-line prayer focus drawn from the day's points.
- **Resources.** List only images and activity sheets that exist in `2026_classes/Images/` and `2026_classes/activities/` and fit this lesson. Leave the headings with a `- ` placeholder if none fit. Never invent a file.
- **Planning reference.** Say which source assigned the lesson, and that the plan follows the format of the previous week's plan (wikilink).
- **Transcript.** End with an empty `## Transcript` heading. Add `transcript:` and `recording:` front matter only when those files exist.

Use KJV Bible Gateway links in this form: `https://www.biblegateway.com/passage/?search=John+4%3A1-26&version=KJV`.

## Links

The repository is an Obsidian vault (it has a `.obsidian/` folder). Read `.obsidian/app.json` before writing any link to a file in the repository and follow it:

- `useMarkdownLinks` absent or `false` → wikilinks. `true` → Markdown links.
- `newLinkFormat` absent or `"shortest"` → the bare file name (no `.md`) when no other file in the vault has that name; otherwise the path from the vault root, e.g. `[[books/intermediate_4_lessons/Lesson 02 - Title|…]]`. `"absolute"` → always the vault-root path. `"relative"` → the path from the plan.

With the settings at the time of writing (neither key set), that means shortest-path wikilinks such as `[[Lesson 03 - Belief in the Messiah at Samaria|Lesson 03 — Belief in the Messiah at Samaria]]`. Check a name is unique by searching the whole vault for that file name, not just the folder you expect.

## Update the README

After creating the plan, add it to the `## Lesson plans` list in `README.md`. This is the only file besides the new plan that this skill edits.

- One line per plan, in date order, oldest first: `- [[MM_DD|{Month D, YYYY} — {Lesson title}]]`. Take the date from the plan's header line and the title from its `#` heading, e.g. `- [[11_22|November 22, 2026 — Belief in the Messiah at Samaria]]`.
- Follow "Links" for the target. If another year's folder has a plan with the same file name, use the vault path (`[[2026_classes/11_22|…]]`) for every entry with that name, including existing ones, so none are ambiguous.
- Insert the new line; leave the other entries and the rest of the README unchanged. If the plan already has a line (for example, a plan the user asked you to replace), update that line instead of adding another.
- Then check the list against the folders: every `{year}_classes/MM_DD.md` plan has exactly one line, and every line names a plan that exists. Report any mismatch you find rather than silently fixing entries for other weeks.

## When Everett hasn't given his own thinking

Still draft "Lessons for us", but keep it a draft for him to choose from, not a finished argument. Put this callout directly under the `## Lessons for us` heading:

```markdown
> [!todo] Draft points
> These are suggestions from the passage and lesson. Keep, cut or rewrite them before Sunday.
```

Prefer the lesson's own "Lesson for us" section and what the passage plainly shows. Don't stretch for a fourth point if the material gives three.

## Standards

- **Scripture first.** Ground every point in the text. Cite real references only. If you aren't sure of a reference or its wording, say so in a teacher's note instead of guessing.
- **Christadelphian teaching.** One God, the Father; Jesus the Son of God, not God the Son; the holy spirit as God's power; mortal humans with no immortal soul; resurrection and judgement at Christ's return; the Kingdom of God on earth based on the promises to Abraham and David. Where a lesson's wording could be misheard on these points, add a short clarification with Scripture, as `11_15.md` does for being born of water and of the Spirit.
- **Fair to the people in the text.** Don't make the Pharisees, Samaritans or disciples into straw men. Separate what the text says from reasonable guesses about motive, as `11_15.md` does for Nicodemus visiting at night.
- **Fit for teenagers.** Plain words, concrete examples and questions they can actually answer. No hype, "Imagine…" openers, aphorisms or alliteration.
- **Leave the source alone.** Don't edit lesson files, activity sheets or earlier plans. Background links are fine when they're reliable and Everett would recognize their purpose. Say what you used.

## Finish

Check that every link resolves, wikilinks name files that exist, the README list includes the new plan, and the plan reads top to bottom as one class of about an hour. Report the file path, the README line you added, which lesson you chose and why, the readings, any teacher's notes, and anything Everett needs to decide or confirm. Don't commit unless asked.
