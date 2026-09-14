"""裁剪行号列 + 按 92 行/页切割"""
from PIL import Image
from pathlib import Path
import warnings
warnings.filterwarnings('ignore', category=Image.DecompressionBombWarning)
Image.MAX_IMAGE_PIXELS = None

SRC = Path(r"e:\MathModeling_Coworkbench\code\submission\code_images")
OUT = SRC / "split"
OUT.mkdir(exist_ok=True)

LINES_PER_PAGE = 80
TARGET_H = 2943
LINE_H = TARGET_H / LINES_PER_PAGE  # ≈ 37px


def find_line_number_width(img, sample_h=500):
    """检测行号列宽度。行号列右侧通常有间隔（较暗的空白列）。"""
    w, h = img.size
    gray = img.convert('L')
    check_h = min(sample_h, h)

    # 计算每列的平均亮度
    col_avg = []
    for x in range(min(200, w)):
        col = gray.crop((x, 0, x + 1, check_h))
        col_avg.append(sum(col.getdata()) / check_h)

    # 找行号列结束位置：行号列之后通常有一段较暗的间隔
    # 策略：找第一个连续暗列（avg < 30）超过 5px 的位置
    dark_run = 0
    for x, avg in enumerate(col_avg):
        if avg < 30:
            dark_run += 1
            if dark_run >= 5 and x > 20:  # 至少 5px 暗列，且不在最左边
                return x - dark_run + 1  # 行号列宽度
        else:
            dark_run = 0

    # 备用：找亮度突变点
    for x in range(10, len(col_avg) - 5):
        if col_avg[x] - col_avg[x - 1] > 30:
            return x

    return 60  # 默认值


def split_image(fp):
    img = Image.open(fp)
    w, h = img.size

    # 1. 检测并裁剪行号列
    ln_width = find_line_number_width(img)
    print(f"  行号列宽: {ln_width}px")

    code_img = img.crop((ln_width, 0, w, h))
    cw, ch = code_img.size
    print(f"  代码区域: {cw}x{ch}")

    # 2. 按 92 行/页切割
    total_lines = int(ch / LINE_H)
    n_pages = max(1, (total_lines + LINES_PER_PAGE - 1) // LINES_PER_PAGE)

    if n_pages == 1:
        out_name = f"{fp.stem}.png"
        code_img.save(str(OUT / out_name), dpi=(300, 300))
        print(f"  {out_name:30s}  {cw}x{ch}  ({total_lines}行)")
        return 1

    stem = fp.stem
    for i in range(n_pages):
        line_start = i * LINES_PER_PAGE
        line_end = min(line_start + LINES_PER_PAGE, total_lines)
        px_top = int(line_start * LINE_H)
        px_bot = int(line_end * LINE_H)

        page = code_img.crop((0, px_top, cw, px_bot))
        out_name = f"{stem}_p{i+1}.png"
        page.save(str(OUT / out_name), dpi=(300, 300))
        print(f"  {out_name:30s}  {cw}x{px_bot - px_top}  行{line_start+1}-{line_end}")

    return n_pages


files = sorted(SRC.glob("*.png"))
files = [f for f in files if not f.name.startswith('test_') and '_p' not in f.stem]

total_pages = 0
for fp in files:
    n = split_image(fp)
    total_pages += n
    print()

print(f"总计：{total_pages} 页")
