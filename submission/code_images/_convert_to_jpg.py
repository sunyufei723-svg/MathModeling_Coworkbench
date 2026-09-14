"""将 code_images/split/ 下所有 PNG 转为 JPG（quality=70）。"""
from pathlib import Path
from PIL import Image

SPLIT_DIR = Path(__file__).parent / "split"
QUALITY = 70

for png in sorted(SPLIT_DIR.glob("*.png")):
    jpg = png.with_suffix(".jpg")
    img = Image.open(png).convert("RGB")
    img.save(jpg, "JPEG", quality=QUALITY, optimize=True)
    print(f"{png.name} -> {jpg.name}  ({png.stat().st_size/1024:.0f}KB -> {jpg.stat().st_size/1024:.0f}KB)")

print("Done.")
