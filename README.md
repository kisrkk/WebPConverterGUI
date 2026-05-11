# WebPConverterGUI

A batch image-to-WebP converter with both GUI and CLI workflows. The GUI can convert single files or whole folders, preserve subfolder structure in the output directory, and process images in parallel using CPU workers.

## Features

- Convert images to `.webp`
- GUI supports `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tif`, `.tiff`, `.gif`, and `.webp`
- Configurable WebP quality from `1-100`
- Convert one file or an entire folder
- Optional recursive subfolder processing
- Optional overwrite behavior
- CLI supports background removal with `rembg` or a corner-color fallback method

## Install For Python Usage

Python 3 is required. Install the main dependency:

```powershell
pip install pillow
```

To use high-quality background removal in the CLI, install `rembg` as well:

```powershell
pip install rembg
```

## GUI Usage

### Run The Built EXE

If a build is available, run:

```powershell
.\dist\WebPConverterGUI.exe
```

### Run With Python

From the project directory:

```powershell
python .\webp_converter_gui.py
```

In the GUI:

1. Click `File` to select one image, or `Folder` to select an image folder.
2. Choose the `Output` folder.
3. Set `Quality`, for example `90`.
4. Set `CPU workers` as needed.
5. Toggle `Recursive sub-folders` if you want to process nested folders.
6. Toggle `Overwrite output` if you want to replace existing output files.
7. Click `Convert`.

Output files are saved as `.webp` in the selected output folder. When the input is a folder, the GUI preserves the input subfolder structure under the output folder.

## CLI Usage

The CLI script is:

```powershell
python .\bg_remove_webp.py --help
```

Command format:

```powershell
python .\bg_remove_webp.py <input> [options]
```

`<input>` can be an image file or an image folder.

### Convert One File To WebP Without Background Removal

```powershell
python .\bg_remove_webp.py .\input\photo.png --mode none -o .\output
```

By default, the output filename includes the `-nobg` suffix, for example `photo-nobg.webp`, even when using `--mode none`.

To keep the original stem:

```powershell
python .\bg_remove_webp.py .\input\photo.png --mode none --suffix "" -o .\output
```

### Convert A Folder

```powershell
python .\bg_remove_webp.py .\input -o .\output --mode none
```

### Convert A Folder Recursively

```powershell
python .\bg_remove_webp.py .\input -o .\output --recursive --mode none
```

### Remove Backgrounds Automatically And Save As WebP

```powershell
python .\bg_remove_webp.py .\input -o .\output --recursive --mode auto
```

`auto` tries `rembg` first. If `rembg` is not installed, it falls back to `corner-color`.

### Use rembg Only

```powershell
python .\bg_remove_webp.py .\input\photo.png -o .\output --mode rembg
```

Install it first:

```powershell
pip install rembg
```

### Use Corner-Color Background Removal

This works best for images with plain or nearly uniform backgrounds:

```powershell
python .\bg_remove_webp.py .\input -o .\output --recursive --mode corner-color --threshold 34 --feather 0.8
```

### Set WebP Quality

```powershell
python .\bg_remove_webp.py .\input -o .\output --mode none --quality 85
```

`--quality` must be between `1` and `100`.

### Overwrite Existing Files

```powershell
python .\bg_remove_webp.py .\input -o .\output --mode none --overwrite
```

Without `--overwrite`, existing output files are skipped.

## CLI Options

| Option | Description |
| --- | --- |
| `input` | Source image file or folder |
| `-o`, `--output-dir` | Output folder. Defaults to a `webp` folder next to the input |
| `--recursive` | Process subfolders |
| `--mode` | `auto`, `rembg`, `corner-color`, `none` |
| `--quality` | WebP quality from `1-100`. Default: `90` |
| `--suffix` | Suffix added before `.webp`. Default: `-nobg` |
| `--threshold` | Threshold for `corner-color` mode. Default: `34` |
| `--feather` | Alpha edge feather radius for `corner-color` mode. Default: `0.8` |
| `--overwrite` | Replace existing output files |

## Build An EXE

Install PyInstaller:

```powershell
pip install pyinstaller
```

Build from the spec file:

```powershell
pyinstaller .\WebPConverterGUI.spec
```

The built executable is written to:

```text
dist\WebPConverterGUI.exe
```

## Notes

- `run_webp_converter_gui.bat` currently points to `tools\webp_converter_gui.py`, but the script is in the project root. Use `python .\webp_converter_gui.py` or `.\dist\WebPConverterGUI.exe`.
- `corner-color` works best with simple, solid-color backgrounds. Use `rembg` for complex backgrounds.
