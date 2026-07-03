# Photocopy PDF

Turns a folder of phone photos of documents into PDFs that look like they
came out of a photocopier — straightened, cropped to the page, rotated
upright, and cleaned up so the background is white instead of a photo of
a table or desk.

## 1. Install

You need Python 3 installed. Then, in a terminal, go to the folder with
the script and run:

```
pip install -r requirements.txt
```

This installs the tools the script needs: `opencv-python-headless`
(image processing), `numpy` (number crunching for images), `pillow`
(saving the final PDF), and `pytesseract` (reads text on the page to
figure out which way is "up").

**For the best rotation results**, also install Tesseract OCR itself —
`pytesseract` is just a thin wrapper around it, so it won't work without it:

- **Ubuntu/Debian:** `sudo apt-get install tesseract-ocr`
- **macOS:** `brew install tesseract`
- **Windows:** install from https://github.com/UB-Mannheim/tesseract/wiki

  On Windows, the installer often does **not** add Tesseract to your PATH
  automatically, so the script may still say "tesseract not installed"
  even after installing it. If that happens, add it manually:
  1. Note where it was installed (usually `C:\Program Files\Tesseract-OCR`)
  2. Start menu → search "Edit the system environment variables" → open it
  3. Click **Environment Variables**
  4. Under **System variables**, select `Path` → **Edit** → **New**
  5. Paste the folder path from step 1 → **OK** on all windows
  6. **Close and reopen your terminal** (already-open terminals won't see the change)
  7. Check it worked by running `tesseract --version` — it should print a version number

If you skip this, the script still runs — it just falls back to guessing
rotation from the page's width vs. height, which can't tell if a page is
upside-down (only whether it's sideways).

## 2. Run it

```
python photocopy_pdf.py -i /path/to/your/photos -o /path/to/save/pdfs
```

- `-i` is the folder with your `.jpg` / `.jpeg` photos
- `-o` is the folder where the finished PDFs will be saved (one PDF per photo, same file name)

That's it — with no extra options, it will automatically:
1. Find the edges of the page and straighten/crop to just the document
2. Rotate it upright if it was photographed sideways
3. Even out the lighting and convert it to a clean grayscale "scanned" look

## 3. The options, explained simply

You add these after the command above if you want to change how it works.
None of them are required — the defaults are sensible.

### `--mode grayscale` or `--mode bw`
**What look you want the final page to have.**
- `grayscale` (default) — looks like a modern office copier: soft gray
  shading, natural-looking text, white background.
- `bw` — looks like an old-school fax/copier: everything is pure black
  or pure white, no gray at all. Use this if you want smaller, higher-contrast files.

Example:
```
python photocopy_pdf.py -i photos -o pdfs --mode bw
```

### `--contrast 1.3`
**Only affects grayscale mode.** How strong the light/dark difference is.
- Higher number (e.g. `1.6`) = more punchy, background gets whiter, text gets darker
- Lower number (e.g. `1.0`) = softer, more "photo-like"

### `--brightness 10`
**Only affects grayscale mode.** Makes the whole page lighter or darker.
- Positive number = lighter page
- Negative number (e.g. `-15`) = darker page
- Use this if your pages come out looking a bit too dark or washed out

### `--block-size 25` and `--c 15`
**Only affect `bw` mode.** These control how the black/white split decides
what counts as "black text" vs "white background."
- `--block-size`: how big an area it looks at when deciding — bigger
  number = smoother but may lose fine detail
- `--c`: how strict the split is — higher number = more gets pushed to
  white (good if your background looks gray instead of white)

You usually don't need to touch these unless the `bw` result looks wrong.

### `--denoise`
**Cleans up graininess** from photos taken in low light. Makes the result
look cleaner but takes a bit longer to process. Add it like this:
```
python photocopy_pdf.py -i photos -o pdfs --denoise
```

### `--no-perspective`
**Turns off automatic page detection/straightening.** By default, the
script tries to find your document's 4 corners and flatten it like a
scan. If it's getting this wrong on your photos (e.g. cropping too
much, or picking the wrong edges), add this flag to just use the photo
as-is.

### `--no-rotate`
**Turns off automatic upright-rotation.** By default, the script reads
the text on the page to figure out which way is up, and rotates the
page so it's the right way round — even fixing pages that are sideways
or completely upside-down. Add this flag if you'd rather it left every
page exactly as photographed.

### `--rotation-confidence 1.0`
**How sure the rotation check needs to be before trusting it.** The
script reads the text to judge orientation; this number is how
confident it must be before acting on that reading.
- Lower it (e.g. `0.5`) if correct rotations are being skipped
- Raise it (e.g. `2.0`) if it's rotating pages incorrectly
- If it's not confident enough (or Tesseract isn't installed), it falls
  back to a simpler guess based on whether the page is wider than it is tall

### `--dpi 300`
**How much detail/resolution to save in the PDF.** 300 is a standard,
good-quality scan resolution. You generally don't need to change this,
but you could lower it (e.g. `150`) for smaller file sizes, or raise it
(e.g. `600`) if you need to zoom in a lot on the final PDF.

## 4. Reading the output

While it runs, the script prints a line per photo telling you whether it
actually used text-reading (Tesseract) to fix the rotation, or fell back
to the basic guess — and why, if so:

```
→ receipt1.jpg: Tesseract used, rotated 90° (confidence 4.12)
→ receipt2.jpg: Tesseract used, page already upright (confidence 3.05)
→ receipt3.jpg: Tesseract NOT used (tesseract not installed), falling back to basic width-vs-height rotation
→ receipt4.jpg: Tesseract NOT used (confidence too low (0.62 < 1.00)), falling back to basic width-vs-height rotation
→ receipt5.jpg: Tesseract NOT used (no text found on page), falling back to basic width-vs-height rotation
```

Common reasons Tesseract might not be used for a given page:
- **"tesseract not installed"** — the OCR engine isn't set up (see step 1)
- **"no text found on page"** — the photo has too little/no readable text (e.g. a photo, a mostly blank page)
- **"confidence too low"** — Tesseract read the page but wasn't sure enough about the orientation; lower `--rotation-confidence` to accept these
- **"OCR failed (...)"** — Tesseract hit an error reading this specific image

## 5. Examples

Default settings (recommended starting point):
```
python photocopy_pdf.py -i ./my_photos -o ./my_pdfs
```

Old-school stark black-and-white look:
```
python photocopy_pdf.py -i ./my_photos -o ./my_pdfs --mode bw
```

Low-light photos that came out grainy and dark:
```
python photocopy_pdf.py -i ./my_photos -o ./my_pdfs --denoise --brightness 25
```

Photos where the auto-crop keeps getting it wrong:
```
python photocopy_pdf.py -i ./my_photos -o ./my_pdfs --no-perspective
```

## 6. If something looks off

| Problem | Try this |
|---|---|
| Background looks gray, not white | `--mode bw` and raise `--c`, or in grayscale mode raise `--contrast` / `--brightness` |
| Text is too faint / thin | Lower `--contrast` a bit, or raise `--brightness` |
| Page got cropped wrong | Add `--no-perspective` |
| Page is sideways or upside-down | Should auto-correct if Tesseract OCR is installed; otherwise install it (see step 1) — without it, upside-down pages can't be detected |
| Photo is grainy/noisy | Add `--denoise` |