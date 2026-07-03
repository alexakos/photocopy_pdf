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

This installs the three tools the script needs: `opencv-python-headless`
(image processing), `numpy` (number crunching for images), and `pillow`
(saving the final PDF).

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
**Turns off automatic upright-rotation.** By default, if a page comes
out wider than it is tall, the script rotates it to portrait. If you're
scanning something that's genuinely meant to be landscape (like a wide
table or certificate), add this flag to keep it as-is.

### `--dpi 300`
**How much detail/resolution to save in the PDF.** 300 is a standard,
good-quality scan resolution. You generally don't need to change this,
but you could lower it (e.g. `150`) for smaller file sizes, or raise it
(e.g. `600`) if you need to zoom in a lot on the final PDF.

## 4. Examples

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

## 5. If something looks off

| Problem | Try this |
|---|---|
| Background looks gray, not white | `--mode bw` and raise `--c`, or in grayscale mode raise `--contrast` / `--brightness` |
| Text is too faint / thin | Lower `--contrast` a bit, or raise `--brightness` |
| Page got cropped wrong | Add `--no-perspective` |
| Page is sideways | Should auto-rotate; if it's still wrong, check `--no-rotate` isn't set |
| Photo is grainy/noisy | Add `--denoise` |
