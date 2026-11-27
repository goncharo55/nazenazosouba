"""シェア画像 docs/og.png（1200x630）を、ずんだもん＆めたん入りで作る。手元で1回流せばよい（docs/og.png はコミットする）。

素材: C:\\Users\\gonta\\claude\\market_weekly\\assets\\chara（YouTubeと同じ立ち絵。坂本アヒル様）
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).parent
SRC = Path(r"C:\Users\gonta\claude\market_weekly\assets\chara")
W, H = 1200, 630


def bust(name, crop, width):
    im = Image.open(SRC / name).convert("RGBA")
    im = im.crop((0, 0, im.width, int(im.height * crop)))
    return im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)


def main():
    # 背景：上から下へ紺→やや明るい紺のグラデーション
    bg = Image.new("RGB", (W, H))
    px = bg.load()
    for y in range(H):
        t = y / (H - 1)
        c = (round(31 + 18 * t), round(58 + 28 * t), round(95 + 40 * t))
        for x in range(W):
            px[x, y] = c
    d = ImageDraw.Draw(bg)
    # ゆるい折れ線グラフ（背景の飾り）
    pts = [(0, 520), (140, 470), (260, 500), (400, 410), (520, 440), (660, 340), (790, 380), (930, 290), (1060, 320), (1200, 230)]
    d.line(pts, fill=(255, 255, 255, 40), width=6, joint="curve")
    bg = bg.convert("RGBA")
    z = bust("zunda_happy_open.png", 0.40, 420)
    m = bust("metan_happy_open.png", 0.37, 420)
    bg.alpha_composite(z, (-10, H - z.height))
    bg.alpha_composite(m, (W - m.width + 10, H - m.height))
    d = ImageDraw.Draw(bg)
    fb = "C:/Windows/Fonts/YuGothB.ttc"
    f1, f2, f3 = ImageFont.truetype(fb, 74), ImageFont.truetype(fb, 27), ImageFont.truetype(fb, 25)
    cx = W // 2
    for text, font, y, fill in (("なぜなぞ相場", f1, 150, "white"),
                                ("むずかしい値動きを、", f2, 270, (231, 236, 242)),
                                ("やさしい言葉で。", f2, 312, (231, 236, 242)),
                                ("株・為替・金・原油・暗号資産の", f3, 400, (190, 205, 222)),
                                ("値動きの「なぜ？」を毎日解説", f3, 438, (190, 205, 222))):
        w = d.textlength(text, font=font)
        d.text((cx - w / 2, y), text, font=font, fill=fill)
    small = ImageFont.truetype(fb, 15)
    for k, credit in enumerate(("VOICEVOX:ずんだもん / VOICEVOX:四国めたん", "立ち絵：坂本アヒル様")):
        d.text((cx - d.textlength(credit, font=small) / 2, 530 + 24 * k), credit, font=small, fill=(160, 178, 200))
    out = BASE / "docs" / "og.png"
    bg.convert("RGB").save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
