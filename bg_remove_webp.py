#!/usr/bin/env python
"""Remove image backgrounds and export WebP assets.

The best background removal path uses the optional `rembg` package. When it is
not installed, the script can still remove mostly solid backgrounds by sampling
the image corners.
"""

from __future__ import annotations

import argparse
import sys
from io import BytesIO
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageChops, ImageFilter, ImageOps


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description="Remove backgrounds from images and save optimized .webp files."
  )
  parser.add_argument("input", type=Path, help="Input image file or directory.")
  parser.add_argument(
    "-o",
    "--output-dir",
    type=Path,
    default=None,
    help="Output directory. Defaults to a 'webp' folder next to the input.",
  )
  parser.add_argument(
    "--recursive",
    action="store_true",
    help="Process images inside subdirectories when input is a directory.",
  )
  parser.add_argument(
    "--mode",
    choices=("auto", "rembg", "corner-color", "none"),
    default="auto",
    help=(
      "Background removal mode. 'auto' tries rembg first, then falls back to "
      "corner-color. 'none' only converts to WebP."
    ),
  )
  parser.add_argument(
    "--quality",
    type=int,
    default=90,
    help="WebP quality from 1 to 100. Default: 90.",
  )
  parser.add_argument(
    "--suffix",
    default="-nobg",
    help="Suffix added before .webp. Use an empty string to keep the same stem.",
  )
  parser.add_argument(
    "--threshold",
    type=int,
    default=34,
    help="Color distance threshold for corner-color mode. Default: 34.",
  )
  parser.add_argument(
    "--feather",
    type=float,
    default=0.8,
    help="Alpha edge feather radius for corner-color mode. Default: 0.8.",
  )
  parser.add_argument(
    "--overwrite",
    action="store_true",
    help="Overwrite existing output files.",
  )
  return parser.parse_args()


def iter_images(input_path: Path, recursive: bool) -> Iterable[Path]:
  if input_path.is_file():
    if input_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
      raise ValueError(f"Unsupported image extension: {input_path.suffix}")
    yield input_path
    return

  if not input_path.is_dir():
    raise FileNotFoundError(f"Input path not found: {input_path}")

  pattern = "**/*" if recursive else "*"
  for path in sorted(input_path.glob(pattern)):
    if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
      yield path


def output_path_for(source: Path, input_path: Path, output_dir: Path, suffix: str) -> Path:
  if input_path.is_dir():
    relative_parent = source.parent.relative_to(input_path)
    target_dir = output_dir / relative_parent
  else:
    target_dir = output_dir
  return target_dir / f"{source.stem}{suffix}.webp"


def remove_with_rembg(image: Image.Image) -> Image.Image:
  try:
    from rembg import remove
  except ImportError as exc:
    raise RuntimeError("rembg is not installed") from exc

  with BytesIO() as source_buffer:
    image.save(source_buffer, format="PNG")
    result_bytes = remove(source_buffer.getvalue())
  return Image.open(BytesIO(result_bytes)).convert("RGBA")


def average_corner_color(image: Image.Image, sample_size: int = 12) -> tuple[int, int, int]:
  rgb = image.convert("RGB")
  width, height = rgb.size
  sample_size = max(1, min(sample_size, width // 4 or 1, height // 4 or 1))
  boxes = (
    (0, 0, sample_size, sample_size),
    (width - sample_size, 0, width, sample_size),
    (0, height - sample_size, sample_size, height),
    (width - sample_size, height - sample_size, width, height),
  )

  colors: list[tuple[int, int, int]] = []
  for box in boxes:
    crop = rgb.crop(box)
    pixels = list(crop.getdata())
    channels = tuple(sum(pixel[index] for pixel in pixels) // len(pixels) for index in range(3))
    colors.append(channels)

  return tuple(sum(color[index] for color in colors) // len(colors) for index in range(3))


def remove_corner_color_background(
  image: Image.Image,
  threshold: int,
  feather: float,
) -> Image.Image:
  rgba = image.convert("RGBA")
  rgb = rgba.convert("RGB")
  bg = Image.new("RGB", rgb.size, average_corner_color(rgb))
  diff = ImageChops.difference(rgb, bg).convert("L")
  mask = diff.point(lambda value: 255 if value > threshold else 0)
  mask = ImageOps.autocontrast(mask)

  if feather > 0:
    mask = mask.filter(ImageFilter.GaussianBlur(feather))

  rgba.putalpha(mask)
  return rgba


def process_image(source: Path, target: Path, args: argparse.Namespace) -> str:
  if target.exists() and not args.overwrite:
    return "skipped"

  with Image.open(source) as opened:
    image = ImageOps.exif_transpose(opened)
    result = image.convert("RGBA")

    if args.mode in ("auto", "rembg"):
      try:
        result = remove_with_rembg(image)
      except RuntimeError:
        if args.mode == "rembg":
          raise
        result = remove_corner_color_background(image, args.threshold, args.feather)
    elif args.mode == "corner-color":
      result = remove_corner_color_background(image, args.threshold, args.feather)
    elif args.mode == "none":
      result = image.convert("RGBA")

    target.parent.mkdir(parents=True, exist_ok=True)
    result.save(target, "WEBP", quality=args.quality, method=6, lossless=False)

  return "written"


def main() -> int:
  args = parse_args()
  input_path = args.input.resolve()
  output_dir = (
    args.output_dir.resolve()
    if args.output_dir
    else (input_path.parent / "webp" if input_path.is_file() else input_path / "webp")
  )

  if not 1 <= args.quality <= 100:
    print("Error: --quality must be between 1 and 100.", file=sys.stderr)
    return 2

  try:
    images = list(iter_images(input_path, args.recursive))
  except (FileNotFoundError, ValueError) as exc:
    print(f"Error: {exc}", file=sys.stderr)
    return 2

  if not images:
    print("No supported images found.", file=sys.stderr)
    return 1

  counts = {"written": 0, "skipped": 0, "failed": 0}
  for source in images:
    target = output_path_for(source, input_path, output_dir, args.suffix)
    try:
      status = process_image(source, target, args)
      counts[status] += 1
      print(f"{status}: {source} -> {target}")
    except Exception as exc:
      counts["failed"] += 1
      print(f"failed: {source} ({exc})", file=sys.stderr)

  print(
    f"Done. written={counts['written']} skipped={counts['skipped']} "
    f"failed={counts['failed']}"
  )
  return 1 if counts["failed"] else 0


if __name__ == "__main__":
  raise SystemExit(main())
