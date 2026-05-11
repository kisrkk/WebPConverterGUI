#!/usr/bin/env python
"""Tkinter GUI for batch converting images to WebP.

The converter preserves the input directory structure under the selected output
directory and processes files in parallel using the available CPU cores.
"""

from __future__ import annotations

import os
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".gif", ".webp"}


@dataclass(frozen=True)
class ConvertJob:
  source: Path
  target: Path
  original_size: int


@dataclass(frozen=True)
class ConvertResult:
  source: Path
  target: Path
  original_size: int
  output_size: int
  status: str
  error: str = ""


def format_size(size: int) -> str:
  units = ("B", "KB", "MB", "GB")
  value = float(size)
  for unit in units:
    if value < 1024 or unit == units[-1]:
      return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
    value /= 1024
  return f"{size} B"


def save_percent(original_size: int, output_size: int) -> str:
  if original_size <= 0 or output_size <= 0:
    return "-"
  saved = (1 - (output_size / original_size)) * 100
  return f"{saved:.1f}%"


def iter_images(input_path: Path, recursive: bool) -> Iterable[Path]:
  if input_path.is_file():
    if input_path.suffix.lower() in SUPPORTED_EXTENSIONS:
      yield input_path
    return

  pattern = "**/*" if recursive else "*"
  for path in sorted(input_path.glob(pattern)):
    if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
      yield path


def target_for(source: Path, input_path: Path, output_dir: Path) -> Path:
  if input_path.is_dir():
    relative = source.relative_to(input_path)
    return output_dir / relative.with_suffix(".webp")
  return output_dir / source.with_suffix(".webp").name


def build_jobs(input_path: Path, output_dir: Path, recursive: bool, overwrite: bool) -> list[ConvertJob]:
  jobs: list[ConvertJob] = []
  for source in iter_images(input_path, recursive):
    target = target_for(source, input_path, output_dir)
    if target.exists() and not overwrite:
      jobs.append(ConvertJob(source, target, source.stat().st_size))
    else:
      jobs.append(ConvertJob(source, target, source.stat().st_size))
  return jobs


def convert_one(job: ConvertJob, quality: int, overwrite: bool) -> ConvertResult:
  try:
    if job.target.exists() and not overwrite:
      return ConvertResult(
        source=job.source,
        target=job.target,
        original_size=job.original_size,
        output_size=job.target.stat().st_size,
        status="Skipped",
      )

    job.target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(job.source) as opened:
      image = ImageOps.exif_transpose(opened)
      if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        output = image.convert("RGBA")
      else:
        output = image.convert("RGB")
      output.save(job.target, "WEBP", quality=quality, method=6)

    return ConvertResult(
      source=job.source,
      target=job.target,
      original_size=job.original_size,
      output_size=job.target.stat().st_size,
      status="Done",
    )
  except Exception as exc:
    return ConvertResult(
      source=job.source,
      target=job.target,
      original_size=job.original_size,
      output_size=0,
      status="Failed",
      error=str(exc),
    )


class WebPConverterApp(tk.Tk):
  def __init__(self) -> None:
    super().__init__()
    self.title("Batch WebP Converter")
    self.geometry("1180x720")
    self.minsize(980, 560)

    self.input_var = tk.StringVar()
    self.output_var = tk.StringVar()
    self.quality_var = tk.IntVar(value=90)
    self.recursive_var = tk.BooleanVar(value=True)
    self.overwrite_var = tk.BooleanVar(value=True)
    self.workers_var = tk.IntVar(value=max(1, os.cpu_count() or 1))
    self.status_var = tk.StringVar(value="Ready")
    self.progress_var = tk.DoubleVar(value=0)

    self.result_queue: queue.Queue[ConvertResult | tuple[str, int] | tuple[str, str]] = queue.Queue()
    self.running = False
    self.total_jobs = 0
    self.completed_jobs = 0

    self._build_ui()
    self.after(100, self._poll_queue)

  def _build_ui(self) -> None:
    self.columnconfigure(0, weight=1)
    self.rowconfigure(2, weight=1)

    controls = ttk.Frame(self, padding=12)
    controls.grid(row=0, column=0, sticky="ew")
    controls.columnconfigure(1, weight=1)

    ttk.Label(controls, text="Input").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
    ttk.Entry(controls, textvariable=self.input_var).grid(row=0, column=1, sticky="ew", pady=4)
    ttk.Button(controls, text="File", command=self.select_input_file).grid(row=0, column=2, padx=(8, 4), pady=4)
    ttk.Button(controls, text="Folder", command=self.select_input_folder).grid(row=0, column=3, pady=4)

    ttk.Label(controls, text="Output").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
    ttk.Entry(controls, textvariable=self.output_var).grid(row=1, column=1, sticky="ew", pady=4)
    ttk.Button(controls, text="Browse", command=self.select_output_folder).grid(row=1, column=2, columnspan=2, sticky="ew", padx=(8, 0), pady=4)

    options = ttk.Frame(self, padding=(12, 0, 12, 10))
    options.grid(row=1, column=0, sticky="ew")

    ttk.Label(options, text="Quality").pack(side="left")
    ttk.Spinbox(options, from_=1, to=100, textvariable=self.quality_var, width=5).pack(side="left", padx=(6, 18))
    ttk.Label(options, text="CPU workers").pack(side="left")
    ttk.Spinbox(options, from_=1, to=max(1, os.cpu_count() or 1), textvariable=self.workers_var, width=5).pack(side="left", padx=(6, 18))
    ttk.Checkbutton(options, text="Recursive sub-folders", variable=self.recursive_var).pack(side="left", padx=(0, 18))
    ttk.Checkbutton(options, text="Overwrite output", variable=self.overwrite_var).pack(side="left", padx=(0, 18))
    ttk.Button(options, text="Convert", command=self.start_convert).pack(side="right")

    table_frame = ttk.Frame(self, padding=(12, 0, 12, 8))
    table_frame.grid(row=2, column=0, sticky="nsew")
    table_frame.rowconfigure(0, weight=1)
    table_frame.columnconfigure(0, weight=1)

    columns = ("original", "output", "original_size", "output_size", "save", "status")
    self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
    self.tree.heading("original", text="Original")
    self.tree.heading("output", text="Output")
    self.tree.heading("original_size", text="Original Size")
    self.tree.heading("output_size", text="Output Size")
    self.tree.heading("save", text="Save %")
    self.tree.heading("status", text="Status")

    self.tree.column("original", width=310, anchor="w")
    self.tree.column("output", width=310, anchor="w")
    self.tree.column("original_size", width=110, anchor="e")
    self.tree.column("output_size", width=110, anchor="e")
    self.tree.column("save", width=90, anchor="e")
    self.tree.column("status", width=160, anchor="w")

    scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
    scroll_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
    self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
    self.tree.grid(row=0, column=0, sticky="nsew")
    scroll_y.grid(row=0, column=1, sticky="ns")
    scroll_x.grid(row=1, column=0, sticky="ew")

    footer = ttk.Frame(self, padding=(12, 0, 12, 12))
    footer.grid(row=3, column=0, sticky="ew")
    footer.columnconfigure(0, weight=1)
    ttk.Progressbar(footer, variable=self.progress_var, maximum=100).grid(row=0, column=0, sticky="ew", padx=(0, 12))
    ttk.Label(footer, textvariable=self.status_var, width=32).grid(row=0, column=1, sticky="e")

  def select_input_file(self) -> None:
    path = filedialog.askopenfilename(
      title="Select input image",
      filetypes=(("Image files", "*.jpg *.jpeg *.png *.webp *.gif *.bmp *.tif *.tiff"), ("All files", "*.*")),
    )
    if path:
      self.input_var.set(path)
      if not self.output_var.get():
        self.output_var.set(str(Path(path).parent / "webp"))

  def select_input_folder(self) -> None:
    path = filedialog.askdirectory(title="Select input folder")
    if path:
      self.input_var.set(path)
      if not self.output_var.get():
        self.output_var.set(str(Path(path) / "webp"))

  def select_output_folder(self) -> None:
    path = filedialog.askdirectory(title="Select output folder")
    if path:
      self.output_var.set(path)

  def start_convert(self) -> None:
    if self.running:
      messagebox.showinfo("Batch WebP Converter", "Conversion is already running.")
      return

    input_path = Path(self.input_var.get()).expanduser()
    output_dir = Path(self.output_var.get()).expanduser()
    if not input_path.exists():
      messagebox.showerror("Input missing", "Please select a valid input file or folder.")
      return
    if not output_dir:
      messagebox.showerror("Output missing", "Please select an output folder.")
      return

    quality = int(self.quality_var.get())
    if quality < 1 or quality > 100:
      messagebox.showerror("Invalid quality", "Quality must be between 1 and 100.")
      return

    jobs = build_jobs(input_path, output_dir, self.recursive_var.get(), self.overwrite_var.get())
    if not jobs:
      messagebox.showinfo("No images", "No supported image files found.")
      return

    for item in self.tree.get_children():
      self.tree.delete(item)

    self.running = True
    self.total_jobs = len(jobs)
    self.completed_jobs = 0
    self.progress_var.set(0)
    self.status_var.set(f"Queued {self.total_jobs} files")

    thread = threading.Thread(
      target=self._run_convert,
      args=(jobs, quality, self.overwrite_var.get(), max(1, int(self.workers_var.get()))),
      daemon=True,
    )
    thread.start()

  def _run_convert(self, jobs: list[ConvertJob], quality: int, overwrite: bool, workers: int) -> None:
    workers = max(1, min(workers, os.cpu_count() or 1))
    self.result_queue.put(("started", workers))
    with ThreadPoolExecutor(max_workers=workers) as executor:
      futures = [executor.submit(convert_one, job, quality, overwrite) for job in jobs]
      for future in as_completed(futures):
        self.result_queue.put(future.result())
    self.result_queue.put(("finished", "Done"))

  def _poll_queue(self) -> None:
    while True:
      try:
        message = self.result_queue.get_nowait()
      except queue.Empty:
        break

      if isinstance(message, ConvertResult):
        self.completed_jobs += 1
        status = message.status if not message.error else f"{message.status}: {message.error}"
        self.tree.insert(
          "",
          "end",
          values=(
            str(message.source),
            str(message.target),
            format_size(message.original_size),
            format_size(message.output_size) if message.output_size else "-",
            save_percent(message.original_size, message.output_size),
            status,
          ),
        )
        self.progress_var.set((self.completed_jobs / self.total_jobs) * 100)
        self.status_var.set(f"{self.completed_jobs}/{self.total_jobs} files")
      elif isinstance(message, tuple) and message[0] == "started":
        self.status_var.set(f"Running with {message[1]} workers")
      elif isinstance(message, tuple) and message[0] == "finished":
        self.running = False
        self.status_var.set(f"Done: {self.completed_jobs}/{self.total_jobs} files")

    self.after(100, self._poll_queue)


def main() -> None:
  app = WebPConverterApp()
  app.mainloop()


if __name__ == "__main__":
  main()
