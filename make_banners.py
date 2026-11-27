"""記事のテーマ別バナー(イラスト)を ComfyUI(SDXL) で作る。毎日は作らず、テーマ数枚を作って使い回す。

使い方: ComfyUIを起動した状態で  python make_banners.py [テーマ名 ...] [--n 2]
候補は assets/banners_candidates/<テーマ>_<n>.png に出る。気に入った1枚を assets/banners/<テーマ>.webp に採用する
(採用は pick_banner.py <テーマ> <n>)。
"""
import argparse
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, r"C:\Users\gonta\claude\comfyui")
import gen  # noqa: E402

BASE = Path(__file__).parent
CAND = BASE / "assets" / "banners_candidates"
OUT_DIR = Path(r"C:\Users\gonta\claude\comfyui\output")

STYLE = ("flat vector illustration, soft pastel colors, clean minimal composition, wide banner, "
         "friendly infographic style, no people, no text, no letters, no numbers")
NEG = ("text, letters, numbers, words, logo, watermark, signature, people, faces, photo, realistic, "
       "lowres, blurry, worst quality, jpeg artifacts, deformed, dark, gloomy")

THEMES = {
    "semiconductor": "a glowing computer chip on a circuit board with tiny green and blue lines, silicon wafer in the background",
    "rates": "a seesaw balancing a stack of coins and a rising line chart, bond certificates floating, calm blue tones",
    "fx": "a japanese yen coin and a us dollar coin on a balance scale, world map in soft background, arrows",
    "oil": "an oil barrel and an oil pumpjack at sunrise with a small rising line chart, warm orange tones",
    "gold": "a neat stack of shiny gold bars with a small upward arrow, warm golden light",
    "crypto": "a golden round coin with a bitcoin-like symbol floating over a digital network of dots and lines",
    "earnings": "a bar chart and a clipboard report with a magnifying glass, tidy desk from above",
    "ai": "a friendly abstract robot head made of circuits connected to a cloud with glowing nodes",
    "market": "a city skyline with a large rising and falling stock chart line over it, morning light",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("themes", nargs="*")
    ap.add_argument("--n", type=int, default=2)
    a = ap.parse_args()
    CAND.mkdir(parents=True, exist_ok=True)
    for name in (a.themes or THEMES):
        for k in range(1, a.n + 1):
            t0 = time.time()
            files, seed = gen.generate(f"{THEMES[name]}, {STYLE}", negative=NEG, w=1344, h=768,
                                       seed=1000 * (list(THEMES).index(name) + 1) + k, steps=28, cfg=6.5,
                                       prefix=f"banner_{name}")
            shutil.copyfile(OUT_DIR / files[0], CAND / f"{name}_{k}.png")
            print(name, k, "seed", seed, f"{time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
