# WebPConverterGUI

เครื่องมือแปลงรูปภาพเป็น WebP แบบ batch พร้อม GUI และ CLI สำหรับแปลงไฟล์หลายไฟล์/ทั้งโฟลเดอร์ โดย GUI จะรักษาโครงสร้างโฟลเดอร์ย่อยไว้ใน output และประมวลผลแบบหลาย worker ตามจำนวน CPU

## ความสามารถหลัก

- แปลงรูปภาพเป็น `.webp`
- รองรับไฟล์ `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tif`, `.tiff`, `.gif`, `.webp` ใน GUI
- เลือกคุณภาพ WebP ได้ตั้งแต่ `1-100`
- แปลงทั้งไฟล์เดียวหรือทั้งโฟลเดอร์
- เลือกแปลงโฟลเดอร์ย่อยแบบ recursive ได้
- ตั้งค่า overwrite ไฟล์ปลายทางได้
- CLI รองรับการลบพื้นหลังด้วย `rembg` หรือวิธีเทียบสีมุมภาพ

## ติดตั้งสำหรับรันจาก Python

ต้องมี Python 3 และติดตั้ง dependency หลัก:

```powershell
pip install pillow
```

ถ้าต้องการใช้โหมดลบพื้นหลังคุณภาพสูงใน CLI ให้ติดตั้ง `rembg` เพิ่ม:

```powershell
pip install rembg
```

## วิธีใช้งานแบบ GUI

### ใช้ไฟล์สำเร็จรูป

ถ้ามีไฟล์ build แล้ว ให้เปิด:

```powershell
.\dist\WebPConverterGUI.exe
```

### ใช้ผ่าน Python

รันจากโฟลเดอร์โปรเจกต์:

```powershell
python .\webp_converter_gui.py
```

ในหน้าต่าง GUI:

1. กด `File` เพื่อเลือกไฟล์เดียว หรือ `Folder` เพื่อเลือกทั้งโฟลเดอร์
2. เลือก `Output` สำหรับโฟลเดอร์ปลายทาง
3. ตั้งค่า `Quality` เช่น `90`
4. ตั้งค่า `CPU workers` ตามต้องการ
5. เปิด/ปิด `Recursive sub-folders` ถ้าต้องการแปลงโฟลเดอร์ย่อย
6. เปิด/ปิด `Overwrite output` เพื่อเขียนทับไฟล์เดิม
7. กด `Convert`

ผลลัพธ์จะถูกบันทึกเป็น `.webp` ในโฟลเดอร์ output ถ้า input เป็นโฟลเดอร์ โปรแกรมจะรักษาโครงสร้างโฟลเดอร์ย่อยไว้

## วิธีใช้งานแบบ CLI

CLI อยู่ในไฟล์:

```powershell
python .\bg_remove_webp.py --help
```

รูปแบบคำสั่ง:

```powershell
python .\bg_remove_webp.py <input> [options]
```

`<input>` เป็นได้ทั้งไฟล์ภาพหรือโฟลเดอร์ภาพ

### แปลงไฟล์เดียวเป็น WebP โดยไม่ลบพื้นหลัง

```powershell
python .\bg_remove_webp.py .\input\photo.png --mode none -o .\output
```

ผลลัพธ์เริ่มต้นจะมี suffix `-nobg` เช่น `photo-nobg.webp` แม้ใช้ `--mode none`

ถ้าต้องการใช้ชื่อเดิม:

```powershell
python .\bg_remove_webp.py .\input\photo.png --mode none --suffix "" -o .\output
```

### แปลงทั้งโฟลเดอร์

```powershell
python .\bg_remove_webp.py .\input -o .\output --mode none
```

### แปลงทั้งโฟลเดอร์รวมโฟลเดอร์ย่อย

```powershell
python .\bg_remove_webp.py .\input -o .\output --recursive --mode none
```

### ลบพื้นหลังอัตโนมัติแล้วบันทึกเป็น WebP

```powershell
python .\bg_remove_webp.py .\input -o .\output --recursive --mode auto
```

โหมด `auto` จะลองใช้ `rembg` ก่อน ถ้าไม่ได้ติดตั้ง `rembg` จะ fallback ไปใช้โหมด `corner-color`

### ใช้ rembg เท่านั้น

```powershell
python .\bg_remove_webp.py .\input\photo.png -o .\output --mode rembg
```

ต้องติดตั้งก่อน:

```powershell
pip install rembg
```

### ใช้วิธีลบพื้นหลังจากสีมุมภาพ

เหมาะกับภาพที่พื้นหลังเป็นสีเรียบหรือใกล้เคียงกัน:

```powershell
python .\bg_remove_webp.py .\input -o .\output --recursive --mode corner-color --threshold 34 --feather 0.8
```

### ตั้งคุณภาพ WebP

```powershell
python .\bg_remove_webp.py .\input -o .\output --mode none --quality 85
```

ค่า `--quality` ต้องอยู่ระหว่าง `1-100`

### เขียนทับไฟล์เดิม

```powershell
python .\bg_remove_webp.py .\input -o .\output --mode none --overwrite
```

ถ้าไม่ใส่ `--overwrite` โปรแกรมจะข้ามไฟล์ปลายทางที่มีอยู่แล้ว

## ตัวเลือก CLI

| Option | คำอธิบาย |
| --- | --- |
| `input` | ไฟล์หรือโฟลเดอร์ภาพต้นทาง |
| `-o`, `--output-dir` | โฟลเดอร์ปลายทาง ถ้าไม่ระบุจะใช้โฟลเดอร์ `webp` ใกล้กับ input |
| `--recursive` | ประมวลผลโฟลเดอร์ย่อยด้วย |
| `--mode` | `auto`, `rembg`, `corner-color`, `none` |
| `--quality` | คุณภาพ WebP ตั้งแต่ `1-100`, ค่าเริ่มต้น `90` |
| `--suffix` | suffix ก่อน `.webp`, ค่าเริ่มต้น `-nobg` |
| `--threshold` | ค่า threshold สำหรับ `corner-color`, ค่าเริ่มต้น `34` |
| `--feather` | ค่าเบลอขอบ alpha สำหรับ `corner-color`, ค่าเริ่มต้น `0.8` |
| `--overwrite` | เขียนทับไฟล์ปลายทางที่มีอยู่ |

## Build เป็น EXE

ติดตั้ง PyInstaller:

```powershell
pip install pyinstaller
```

Build จากไฟล์ spec:

```powershell
pyinstaller .\WebPConverterGUI.spec
```

ไฟล์ที่ build แล้วจะอยู่ที่:

```text
dist\WebPConverterGUI.exe
```

## หมายเหตุ

- `run_webp_converter_gui.bat` ในโปรเจกต์นี้อ้าง path `tools\webp_converter_gui.py` แต่ไฟล์ปัจจุบันอยู่ที่ root ของโปรเจกต์ จึงแนะนำให้รัน GUI ด้วย `python .\webp_converter_gui.py` หรือ `.\dist\WebPConverterGUI.exe`
- โหมด `corner-color` เหมาะกับภาพพื้นหลังสีเรียบ ถ้าภาพพื้นหลังซับซ้อนควรใช้ `rembg`
