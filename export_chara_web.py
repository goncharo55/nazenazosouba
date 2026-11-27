"""サイト用のキャラ画像（顔〜肩）を書き出す。

素材: C:\\Users\\gonta\\claude\\market_weekly\\assets\\chara（YouTubeと同じ立ち絵。坂本アヒル様）
出力: assets/chara_web/<chara>_<表情>_<open|closed>.webp  → build_site.py が docs/img/chara/ にコピーする
"""
from pathlib import Path
from PIL import Image

SRC = Path(r"C:\Users\gonta\claude\market_weekly\assets\chara")
OUT = Path(__file__).parent / "assets" / "chara_web"
# 上から何割までを切り出すか(頭〜肩)。素材ごとに寸法が違うので割合で指定
CROP_H = {"zunda": 0.40, "metan": 0.37}
WIDTH = 300  # 表示は150px前後。2倍密度ぶん


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    n = 0
    for p in sorted(SRC.glob("*.png")):
        who = p.stem.split("_")[0]
        im = Image.open(p).convert("RGBA")
        w, h = im.size
        im = im.crop((0, 0, w, int(h * CROP_H[who])))
        im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
        im.save(OUT / (p.stem + ".webp"), "WEBP", quality=88, method=6)
        n += 1
    print("exported", n, "->", OUT)


if __name__ == "__main__":
    main()
