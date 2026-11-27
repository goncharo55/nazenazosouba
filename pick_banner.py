"""バナー候補から1枚を採用する。  python pick_banner.py <テーマ> <番号>
assets/banners_candidates/<テーマ>_<番号>.png を、中央を切り出して 1000x430 の webp にして assets/banners/<テーマ>_<番号>.webp に置く（テーマごとに複数置くと、日付で使い分ける）。
"""
import sys
from pathlib import Path

from PIL import Image

BASE = Path(__file__).parent
W, H = 1000, 430


def main():
    theme, n = sys.argv[1], sys.argv[2]
    src = BASE / "assets" / "banners_candidates" / f"{theme}_{n}.png"
    im = Image.open(src).convert("RGB")
    # 幅1000に縮小 → 縦の中央を切り出す
    h = round(im.height * W / im.width)
    im = im.resize((W, h), Image.LANCZOS)
    top = max(0, (h - H) // 2)
    im = im.crop((0, top, W, top + H))
    out = BASE / "assets" / "banners"
    out.mkdir(parents=True, exist_ok=True)
    im.save(out / f"{theme}_{n}.webp", "WEBP", quality=82, method=6)
    print("picked", src.name, "->", out / f"{theme}_{n}.webp")


if __name__ == "__main__":
    main()
