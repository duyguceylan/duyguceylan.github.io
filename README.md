# Duygu Ceylan - personal website

A small, content-driven static website. Everything on the page is rendered
from a handful of plain-text source files. There is no CMS and no database: to
publish a change you edit a file, run one build command, and copy the output
directory to any static host.

The same conventions used at kaanaksit.com apply here, in a lighter form:

- publications come from a single BibTeX file
- identity, socials, awards, and the thesis come from one JSON file
- news items are one small Markdown file each
- the layout lives in one template

## Layout

    data/           source content (edit these)
      resume.json   who the site is about, socials, awards, education, thesis
      publications.bib   every publication in the "Publications" section
    news/           one Markdown file per announcement
    assets/         the portrait, stylesheet, and a few lines of JavaScript
    templates/      the single-page HTML layout (Jinja2)
    build.py        builds dist/ from the sources above
    dist/           generated output (do not edit; safe to delete)

## Prerequisites

Python 3.9 or newer. The build needs three packages:

    pip install jinja2 markdown pyyaml

(`requirements.txt` lists them for convenience: `pip install -r requirements.txt`.)

## Build

From the project root:

    python3 build.py

This writes the whole site to `dist/`:

    dist/
      index.html
      assets/style.css
      assets/main.js
      assets/profile.jpg

## Preview locally

    python3 build.py
    cd dist && python3 -m http.server 8123

then open http://127.0.0.1:8123/

## How to update each part

### New publication

`data/publications.bib` holds one block per paper. Copy an existing block,
change the first line to a new unique key, and edit the fields. A field you do
not set is simply not shown.

    @inproceedings{yourkey2025,                 % unique key (first token)
      title     = {A Cool New Paper},           % required
      author    = {Some, Alice and Ceylan, Duygu and Other, Bob},
      year      = {2025},                       % required for grouping
      booktitle = {SIGGRAPH 2025},              % venue (conferences and journals)
      note      = {Oral Paper},                 % optional highlight
      url       = {https://arxiv.org/abs/XXXX.XXXXX},   % shown as "Paper"
      project   = {https://example.com},        % optional, shown as "Project"
      code      = {https://github.com/...},     % optional, shown as "Code"
      video     = {https://youtube.com/...},    % optional, shown as "Video"
      slides    = {https://...pdf},             % optional
      supplement = {https://...pdf},            % optional
      preview   = {assets/pubs/yourkey2025.webp}, % optional, image on the left
    }

Notes:

- List authors as `Last, First and Last, First, ...`. The name that matches
  "Duygu Ceylan" (set in resume.json) is automatically highlighted.
- Put the most recent papers at the top of the file. Within a year the file
  order is preserved; the years are grouped newest-first automatically.
- `booktitle` is used for both conferences and journals (for example
  "ACM Transactions on Graphics"). If the venue text already contains the
  year, the year is not repeated; if it does not, it is appended.
- `preview` is an optional image shown on the left of the entry. Drop the
  file into `assets/pubs/` and point the field at it (for example
  `assets/pubs/yourkey2025.webp`; WebP is preferred because it stays small).
  The whole image is always shown, never cropped. The thumbnail links to the
  project URL, or the paper URL if there is no project.

### Identity, socials, awards, thesis

`data/resume.json`. All strings may contain simple inline HTML, so you can put
links where you like.

- `about`: an array of paragraphs shown in the header.
- `socials`: an array of `{ "label": ..., "url": ... }`.
- `quick_links`: buttons under the bio (for example the Full CV PDF).
- `experience` and `education`: arrays shown under "Background".
- `awards`: array of `{ "year": ..., "title": ... }`.
- `thesis`: one object for the PhD thesis, including its download `url`. An
  optional `preview` (for example `assets/thesis.png`) shows an image on the
  left of the thesis card, linked to the paper.
- `photo`: the file name (inside `assets/`) of the portrait. Replace
  `assets/profile.jpg` with a new image of the same name to swap the photo.

### A news item

Create a new file in `news/`. Suggested name: `YYYY-MM-DD-short-slug.md`.

    ---
    date: 2026-10-13
    title: Short headline (optional)
    ---

    Write the announcement here. Markdown is supported, including links and
    lists.

Items are listed newest first. The `date` front matters is required; `title`
is optional.

## Deployment

`dist/` is a self-contained static directory. Any of the following work:

- Point the `dist/` folder at any web server.
- GitHub Pages, Netlify, Cloudflare Pages, or S3 by uploading `dist/` on every
  push.
- A `CNAME` file is included so that when this repository is hosted on a
  matching domain the site resolves there.

## Commit messages

Follow the convention `<emoji> <topic>: <message>`, for example:

    ✍️ content: add Track4Gen to SIGGRAPH 2025
    📰 news: announce Eurographics award
