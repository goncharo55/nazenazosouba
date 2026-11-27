"""トップ・記事ページの「見た目」の部品。数字はすべて記事の指標カード(＝マスタデータ検証済み)から作る。

- talk_html(edition)      : ずんだもん＆めたんの「きょうのひとこと」(掛け合い)
- weather_html(edition)   : 日本株・米国株・半導体の「相場の天気」アイコン
- sparkline(...)          : 指標カードのミニ折れ線(直近約1か月)。カードの値と合わない系列は出さない
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

BASE = Path(__file__).parent
DATA = BASE / "data"
SITE_IMG = "/img/chara"  # SITE_ROOT は空(独自ドメイン直下)


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


# ------------------------------------------------------------------ 履歴(ミニ折れ線用)
_HIST: dict | None = None


def _history() -> dict:
    """{サイト上のticker: {日付: 終値}}。data/history.json を土台に、market_*.json の history で上書き。"""
    global _HIST
    if _HIST is not None:
        return _HIST
    h: dict = {}
    p = DATA / "history.json"
    if p.exists():
        for t, rows in json.loads(p.read_text(encoding="utf-8")).items():
            h[t] = {d: v for d, v in rows}
    for mp in sorted(DATA.glob("market_*.json")):
        try:
            mk = json.loads(mp.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for t, rows in (mk.get("history") or {}).items():
            h.setdefault(t, {}).update({d: v for d, v in rows})
    _HIST = h
    return h


def series_for(ticker: str, edition_date: str, card_value: str, n: int = 30, live: bool = False):
    """カードの値と最終点が一致する系列だけ返す(一致しなければ None＝グラフを出さない)。
    live=True(時刻つきのカード＝その時点の値)は、前日までの終値＋カードの値で描く。"""
    rows = _history().get(ticker)
    if not rows:
        return None
    try:
        target = float(str(card_value).replace(",", ""))
    except ValueError:
        return None
    if live:
        prior = [rows[d] for d in sorted(d for d in rows if d < edition_date)][-(n - 1):]
        return prior + [target] if len(prior) >= 5 else None
    dates = sorted(d for d in rows if d <= edition_date)
    # 最終点を、カードの値に一致する日まで巻き戻して探す（日本は当日、米国は前営業日の終値のため）
    for back in range(0, 5):
        if len(dates) - back < 6:
            return None
        sub = dates[:len(dates) - back]
        last = rows[sub[-1]]
        if abs(last - target) <= max(abs(target) * 0.0006, 0.006):
            return [rows[d] for d in sub[-n:]]
    return None


def sparkline(vals: list[float], up: bool, w: int = 120, h: int = 30) -> str:
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1.0
    pad = 3
    xs = [pad + (w - 2 * pad) * i / (len(vals) - 1) for i in range(len(vals))]
    ys = [pad + (h - 2 * pad) * (1 - (v - lo) / span) for v in vals]
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area = f"{xs[0]:.1f},{h} " + pts + f" {xs[-1]:.1f},{h}"
    cls = "up" if up else "down"
    return (f'<svg class="spark {cls}" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
            f'aria-label="直近約1か月の推移" preserveAspectRatio="none">'
            f'<polygon class="spark-area" points="{area}"/><polyline class="spark-line" points="{pts}" fill="none"/>'
            f'<circle class="spark-dot" cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="2.4"/></svg>')


# ------------------------------------------------------------------ 相場の天気
def _card(ed: dict, ticker: str):
    for i in ed.get("indices") or []:
        if i.get("ticker") == ticker:
            return i
    return None


_SUN = '<circle cx="24" cy="24" r="9" fill="#F6B73C"/><g stroke="#F6B73C" stroke-width="3" stroke-linecap="round"><path d="M24 5v5M24 38v5M5 24h5M38 24h5M10.6 10.6l3.5 3.5M33.9 33.9l3.5 3.5M10.6 37.4l3.5-3.5M33.9 14.1l3.5-3.5"/></g>'
_CLOUD = '<path d="M14 36a8 8 0 0 1-.9-15.9A10.5 10.5 0 0 1 33.4 17 9 9 0 0 1 34 36z" fill="#B7C3CF"/>'
_CLOUD_D = '<path d="M14 34a8 8 0 0 1-.9-15.9A10.5 10.5 0 0 1 33.4 15 9 9 0 0 1 34 34z" fill="#8E9CAA"/>'
_RAIN = '<g stroke="#4A8AC4" stroke-width="3" stroke-linecap="round"><path d="M16 38l-2 5M24 38l-2 5M32 38l-2 5"/></g>'
_BOLT = '<path d="M26 30l-6 9h5l-2 7 8-11h-5z" fill="#F6B73C"/>'


def weather(pct: float) -> tuple[str, str, str]:
    """(ラベル, svg中身, 区分)。数字の閾値だけで決める(予想ではなく、きょうの結果の表現)。"""
    if pct >= 1.0:
        return "晴れ", _SUN, "sun"
    if pct >= 0.3:
        return "うす晴れ", f'<g transform="translate(-4,-5) scale(.95)">{_SUN}</g><g transform="translate(6,4) scale(.78)">{_CLOUD}</g>', "sun"
    if pct > -0.3:
        return "くもり", _CLOUD, "cloud"
    if pct > -1.0:
        return "小雨", _CLOUD_D + _RAIN, "rain"
    if pct > -2.5:
        return "雨", _CLOUD_D + _RAIN, "rain"
    return "雷雨", _CLOUD_D + _BOLT, "rain"


def weather_html(ed: dict) -> str:
    items = [("日本株", "^N225"), ("米国株", "^GSPC"), ("半導体", "^SOX")]
    out = []
    for label, tk in items:
        c = _card(ed, tk)
        if not c or c.get("pct") is None:
            continue
        pct = float(c["pct"])
        name, svg, kind = weather(pct)
        sign = "+" if pct >= 0 else ""
        out.append(f'<div class="wx wx-{kind}"><svg viewBox="0 0 48 48" width="44" height="44" aria-hidden="true">{svg}</svg>'
                   f'<div class="wx-txt"><span class="wx-label">{label}</span><span class="wx-name">{name}</span>'
                   f'<span class="wx-pct">{sign}{pct:.2f}%</span></div></div>')
    if not out:
        return ""
    return (f'<div class="wx-row" aria-label="きょうの相場の天気">{"".join(out)}</div>')


# ------------------------------------------------------------------ きょうのひとこと
def _pick(seed: str, key: str, options: list[str]) -> str:
    h = int(hashlib.sha1(f"{seed}:{key}".encode()).hexdigest(), 16)
    return options[h % len(options)]


def _val0(c: dict) -> str:
    """'57,499.16' -> '57,499'（日経平均の表示は円未満を落とす）"""
    return str(c["value_text"]).split(".")[0]


def mood(pct: float) -> str:
    if pct >= 2.0:
        return "big_up"
    if pct >= 0.5:
        return "up"
    if pct > -0.5:
        return "flat"
    if pct > -2.0:
        return "down"
    return "big_down"


# 気分 → (ずんだもん, めたん) の表情
_FACES = {"big_up": ("happy", "surprise"), "up": ("happy", "happy"), "flat": ("normal", "think"),
          "down": ("trouble", "think"), "big_down": ("surprise", "trouble")}


def _dir(pct: float, up: str, down: str, flat: str) -> str:
    if pct >= 0.15:
        return up
    if pct <= -0.15:
        return down
    return flat


def _plain(t) -> str:
    return re.sub(r"<[^>]+>", "", str(t or ""))


def _first_sentence(text: str, maxlen: int = 80) -> tuple[str, bool]:
    """最初の1文。長すぎるときは読点の位置で切って末尾に…を付ける。(文, 切ったか)"""
    t = _plain(text).strip()
    s = t.split("。")[0] + "。" if "。" in t else t
    if len(s) <= maxlen:
        return s, False
    cut = s[:maxlen]
    k = cut.rfind("、")
    return (cut[:k] if k >= 24 else cut) + "…", True


def _tone(s: str, who: str) -> str:
    """記事の文(です・ます調/常体)を、キャラの口調に近づける。意味は変えず文末だけ。"""
    s = s.rstrip()
    if who == "zunda":
        if s.endswith("です。"):
            return s[:-3] + "なのだ。"
        if s.endswith(("た。", "る。", "う。", "く。", "す。", "ぐ。", "む。", "ぶ。", "つ。")):
            return s[:-1] + "のだ。"
    else:
        if s.endswith("です。"):
            return s[:-3] + "よ。"
        if s.endswith("ます。"):
            return s[:-1] + "わ。"
        if s.endswith(("た。", "る。", "う。", "く。", "す。", "ぐ。", "む。", "ぶ。", "つ。")):
            return s[:-1] + "のよ。"
        if s.endswith("だ。"):
            return s[:-2] + "なのよ。"
    return s


def _lesson_term(title: str) -> str | None:
    t = _plain(title).strip()
    t = re.sub(r"^きょうの用語解説[：:]\s*", "", t).split("―")[0].strip()
    t = re.sub(r"とは[？?]?$", "", t).strip()
    if not t or len(t) > 32:
        return None
    return t.strip("「」 ") if t.startswith("「") and t.count("「") == 1 else t


def _top_mover(ed: dict):
    """理由つきの個別銘柄のうち、騰落率の絶対値がいちばん大きいもの。"""
    best = None
    for m in ed.get("movers") or []:
        if m.get("market") not in ("JP", "US") or len(_first_sentence(m.get("reason"), 200)[0]) < 18:
            continue  # 理由が空、または「○○大手。」のような説明だけの銘柄は使わない
        try:
            p = float(m["pct"])
        except (KeyError, TypeError, ValueError):
            continue
        if best is None or abs(p) > abs(best[0]):
            best = (p, m)
    return best


# 「いちばん動いた指標」の候補（VIX・米10年金利は変化率が大きく出やすいので除く）
_BIG_MOVE_SKIP = {"^N225", "1306.T", "^VIX", "^TNX", "^GSPC"}


def _biggest_index(ed: dict):
    best = None
    for c in ed.get("indices") or []:
        if c.get("ticker") in _BIG_MOVE_SKIP or c.get("pct") is None:
            continue
        if best is None or abs(float(c["pct"])) > abs(float(best["pct"])):
            best = c
    return best


def talk_lines(ed: dict) -> list[tuple[str, str, str]]:
    """[(話者 'zunda'|'metan', 表情, セリフHTML)]。

    その日の記事にしかない内容(いちばん動いた銘柄とその理由・用語解説・いちばん動いた指標)を入れて、毎日同じ掛け合いにならないようにする。
    数字は指標カードと movers の値だけ(どちらも検証済み)。"""
    seed = ed.get("edition_date", "")
    n = _card(ed, "^N225")
    if not n:
        return []
    npct = float(n["pct"])
    m = mood(npct)
    zf, mf = _FACES[m]
    ap = f"{abs(npct):.2f}"
    num = f'<span class="num">{_val0(n)}円</span>'
    z1 = {
        "big_up": [f"きょうの日経平均は{num}、{ap}%も上がったのだ！すごいのだ！"],
        "up": [f"きょうの日経平均は{num}、前日より{ap}%上がったのだ！", f"日経平均は{ap}%の上昇で{num}なのだ！"],
        "flat": [f"日経平均は{num}で、ほとんど動かなかったのだ。", f"きょうの日経平均は{ap}%の小さな動きで{num}なのだ。"],
        "down": [f"きょうの日経平均は{num}、{ap}%下がったのだ…", f"日経平均は{ap}%下がって{num}なのだ…"],
        "big_down": [f"日経平均が{ap}%も下がって{num}になったのだ！びっくりなのだ！"],
    }[m]
    lines = [("zunda", zf, _pick(seed, "z1", z1))]

    # めたん：いちばん大きく動いた指標＋アメリカ株
    parts = []
    big = _biggest_index(ed)
    if big:
        p = float(big["pct"])
        a = f'<span class="num">{abs(p):.2f}%</span>'
        if big.get("ticker") == "USDJPY=X":
            what = f'ドル円で、{"円安" if p > 0 else "円高"}方向に{a}動いたわ。'
        else:
            what = f'{_esc(big["name"])}で、{a}{"上がった" if p > 0 else "下がった"}わ。'
        parts.append("指標でいちばん大きく動いたのは" + what)
    sp = _card(ed, "^GSPC")
    if sp and sp.get("pct") is not None:
        p = float(sp["pct"])
        mv = _dir(p, f'<span class="num">{abs(p):.2f}%</span>上がったわ。', f'<span class="num">{abs(p):.2f}%</span>下がったわ。',
                  "ほとんど動かなかったわ。")
        parts.append(f"アメリカのS&amp;P500は前の日に{mv}")
    if parts:
        lines.append(("metan", mf, " ".join(parts)))

    # ずんだもん：理由つきでいちばん動いた銘柄。なければキーワード
    tm = _top_mover(ed)
    if tm:
        p, mv = tm
        reason, cut = _first_sentence(mv["reason"], 80)
        lead = _pick(seed, "z2", ["銘柄だと", "個別では", "注目は"])
        head = f'{lead}{_esc(mv["name"])}が<span class="num">{abs(p):.2f}%</span>{"上がった" if p > 0 else "下がった"}のだ。'
        tail = "くわしくは下の記事で読めるのだ！" if cut else ""
        lines.append(("zunda", "surprise" if abs(p) >= 8 else ("happy" if p > 0 else "trouble"),
                      f"{head}{_esc(_tone(reason, 'zunda'))}{tail}"))
    else:
        tags = [t.lstrip("#") for t in (ed.get("tags") or [])][:2]
        if tags:
            kw = "・".join(f"「{_esc(t)}」" for t in tags)
            lines.append(("zunda", "normal", f"きょうのキーワードは{kw}なのだ。くわしい理由は下の記事で読めるのだ！"))

    # めたん：きょうの用語解説
    term = _lesson_term(ed.get("lesson_title", ""))
    if term:
        body = (ed.get("lesson_body_paragraphs") or [ed.get("lesson_body", "")] or [""])[0]
        sent, _ = _first_sentence(body, 100)
        txt = (f"きょうの用語解説では、{_esc(term)}という疑問を取り上げているわ。" if "？" in term or "?" in term
               else f"きょうの用語は「{_esc(term)}」よ。")
        if "とは、" in sent:
            txt += "ひとことで言うと、" + _esc(_tone(sent.split("とは、", 1)[1], "metan"))
        elif sent:
            txt += _esc(_tone(sent, "metan"))
        lines.append(("metan", "think", txt))

    # ずんだもん：クイズへの誘い
    if ed.get("quiz"):
        lines.append(("zunda", "happy", _pick(seed, "z3", [
            '最後に<a href="#quiz">なぞなぞクイズ</a>があるのだ。めたんが問題を出すのだ！',
            '記事のあとの<a href="#quiz">きょうのクイズ</a>に挑戦してほしいのだ！'])))
    return lines


def _avatar(who: str, expr: str) -> str:
    base = f"{SITE_IMG}/{who}_{expr}"
    alt = "ずんだもん" if who == "zunda" else "四国めたん"
    return (f'<div class="av av-{who}"><img class="av-closed" src="{base}_closed.webp" alt="{alt}" width="150" height="{_H[who]}" loading="lazy" decoding="async">'
            f'<img class="av-open" src="{base}_open.webp" alt="" aria-hidden="true" width="150" height="{_H[who]}" loading="lazy" decoding="async"></div>')


_H = {"zunda": 125, "metan": 115}  # 300px幅の書き出し画像(300x250 / 300x229)の縦横比から、width=150 のときの高さ


def talk_html(ed: dict) -> str:
    lines = talk_lines(ed)
    if not lines:
        return ""
    rows = []
    for who, expr, text in lines:
        name = "ずんだもん" if who == "zunda" else "めたん"
        rows.append(f'<div class="talk-row talk-{who}">{_avatar(who, expr)}'
                    f'<div class="bubble"><span class="who">{name}</span><p>{text}</p></div></div>')
    return (f'<section class="talk" aria-label="きょうのひとこと"><p class="talk-label">きょうのひとこと</p>'
            f'{"".join(rows)}'
            f'<p class="talk-credit">キャラクター：VOICEVOX:ずんだもん／VOICEVOX:四国めたん（立ち絵：坂本アヒル様）</p></section>')


def video_cta_html(youtube_url: str) -> str:
    """YouTube(週刊なぜなぞ相場)への案内カード。動画IDに依存しない(未公開・非公開でも壊れない)。"""
    if not youtube_url:
        return ""
    def av(who: str) -> str:
        return (f'<img src="{SITE_IMG}/{who}_happy_closed.webp" alt="" width="150" height="{_H[who]}" '
                f'loading="lazy" decoding="async">')
    return (f'<section class="video-cta"><div class="vc-av">{av("zunda")}{av("metan")}</div>'
            f'<div class="vc-body"><p class="vc-title">毎週木曜は、動画でも解説しています</p>'
            f'<p class="vc-text">ずんだもんと四国めたんが、1週間の株・為替・金・ビットコインの値動きを、'
            f'数字といっしょにやさしく話します。</p>'
            f'<a class="vc-btn" href="{_esc(youtube_url)}" target="_blank" rel="noopener">YouTubeで見る</a></div></section>')


# ------------------------------------------------------------------ テーマ別バナー
BANNER_DIR = BASE / "assets" / "banners"
THEME_LABEL = {"semiconductor": "半導体", "ai": "AI", "rates": "金利", "fx": "為替", "oil": "原油", "gold": "金",
               "crypto": "暗号資産", "earnings": "決算", "market": "株式市場"}
THEME_WORDS = {
    "semiconductor": ["半導体", "SOX", "エヌビディア", "キオクシア", "アドバンテスト", "東京エレクトロン", "マイクロン", "チップ", "ルネサス"],
    "ai": ["AI", "OpenAI", "生成AI", "データセンター", "アンソロピック"],
    "rates": ["金利", "利上げ", "利下げ", "FOMC", "日銀", "国債", "債券", "FRB"],
    "fx": ["円安", "円高", "ドル円", "為替", "介入"],
    "oil": ["原油", "WTI", "石油", "OPEC", "中東", "ホルムズ"],
    "gold": ["金価格", "ゴールド", "NY金", "金が", "金は", "金の", "金と銀", "金・銀", "金相場", "金や"],
    "crypto": ["ビットコイン", "暗号資産", "仮想通貨", "イーサリアム"],
    "earnings": ["決算"],
}


def pick_theme(ed: dict) -> str:
    """見出し(3点)・タグ(2点)・1行目の要約(1点)に出てくる語で、記事のテーマを1つ選ぶ。"""
    head = ed.get("headline", "")
    tags = " ".join(ed.get("tags") or [])
    first = (ed.get("summary") or [""])[0]
    best, best_score = "market", 0
    for theme, words in THEME_WORDS.items():
        sc = sum(3 for w in words if w in head) + sum(2 for w in words if w in tags) + sum(1 for w in words if w in first)
        if sc > best_score:
            best, best_score = theme, sc
    return best


def banner_html(ed: dict) -> str:
    """テーマのバナーを1枚。テーマごとに複数ある場合は、日付で決定的に選ぶ(同じ日は常に同じ絵)。"""
    theme = pick_theme(ed)
    files = sorted(BANNER_DIR.glob(f"{theme}_*.webp")) or sorted(BANNER_DIR.glob("market_*.webp"))
    if not files:
        return ""
    f = files[int(hashlib.sha1(ed.get("edition_date", "").encode()).hexdigest(), 16) % len(files)]
    label = THEME_LABEL.get(theme, "株式市場")
    return (f'<div class="banner"><img src="/img/banners/{f.name}" width="1000" height="430" '
            f'alt="{label}のイラスト" decoding="async" fetchpriority="high"></div>')


# ------------------------------------------------------------------ CSS
CSS = """
  /* ---- きょうのひとこと（キャラの掛け合い） ---- */
  .talk { margin: 0 0 28px; background: var(--surface); border:1px solid var(--line); border-radius:14px;
    padding: 16px 18px 12px; box-shadow: var(--shadow); }
  .talk-label { font-family:'IBM Plex Mono',monospace; font-size:12px; letter-spacing:0.08em; color: var(--brand); margin:0 0 6px; }
  .talk-row { display:grid; grid-template-columns: 118px minmax(0, 1fr); column-gap:16px; align-items:start; margin: 10px 0; }
  .av { position:relative; width:118px; }
  .av img { display:block; width:118px; height:auto; }
  .av .av-open { position:absolute; left:0; top:0; opacity:0; animation: mouth .46s steps(1) 4; }
  @keyframes mouth { 0% { opacity:1; } 50% { opacity:0; } }
  @media (prefers-reduced-motion: reduce) { .av .av-open { animation:none; } }
  .bubble { position:relative; min-width:0; border:1px solid var(--line); border-radius:14px; padding:10px 16px;
    font-size:15.5px; line-height:1.75; background: var(--surface-2); }
  .talk-zunda .bubble { background: color-mix(in srgb, #7BC96F 13%, var(--surface)); }
  .talk-metan .bubble { background: color-mix(in srgb, #E86AA6 11%, var(--surface)); }
  .bubble p { margin:0; }
  .bubble .who { display:block; font-size:11.5px; font-weight:600; margin-bottom:1px; }
  .talk-zunda .who { color:#3E8E2F; } .talk-metan .who { color:#C0407E; }
  .bubble::before { content:""; position:absolute; top:22px; left:-7px; width:12px; height:12px; transform: rotate(45deg);
    border-left:1px solid var(--line); border-bottom:1px solid var(--line); background: inherit; }
  .talk-credit { font-size:10.5px; color: var(--ink-faint); margin:8px 0 0; text-align:right; }
  @media (max-width: 560px) {
    .talk { padding: 12px 12px 10px; }
    .talk-row { grid-template-columns: 62px minmax(0, 1fr); column-gap:12px; }
    .av { width:62px; } .av img { width:62px; }
    .bubble { font-size:14.5px; padding:8px 12px; }
  }

  /* ---- 相場の天気 ---- */
  .wx-row { display:flex; gap:10px; flex-wrap:wrap; margin: 0 0 22px; }
  .wx { display:flex; align-items:center; gap:8px; background: var(--surface); border:1px solid var(--line);
    border-radius:12px; padding:8px 14px 8px 10px; min-width: 0; }
  .wx-txt { display:flex; flex-direction:column; line-height:1.25; }
  .wx-label { font-size:11px; color: var(--ink-faint); }
  .wx-name { font-size:16px; font-weight:600; color: var(--ink); white-space:nowrap; }
  .wx-pct { font-family:'IBM Plex Mono',monospace; font-size:12px; color: var(--ink-soft); }
  .wx-sun { border-color:#F3DDA8; } .wx-rain { border-color:#C6D8EA; }
  @media (max-width: 560px) { .wx-row { gap:6px; } .wx { padding:6px 9px 6px 6px; gap:5px; flex:1 1 30%; }
    .wx svg { width:30px; height:30px; flex:0 0 30px; } .wx-name { font-size:13.5px; } .wx-pct { font-size:11px; } }

  /* ---- 指標カードのミニ折れ線 ---- */
  .ticker-card .t-spark { margin-top:8px; line-height:0; }
  .spark { width:100%; height:30px; display:block; }
  .spark-line { stroke-width:1.5; vector-effect: non-scaling-stroke; stroke-linejoin:round; stroke-linecap:round; }
  .spark-line { stroke: var(--ink-faint); }
  .spark-area { fill: var(--ink-faint); opacity:.12; }
  .spark.up .spark-dot { fill: var(--up); } .spark.down .spark-dot { fill: var(--down); }
  @media (max-width: 560px) { .spark { height:22px; } .ticker-card .t-spark { margin-top:5px; } }

  /* ---- YouTube案内カード ---- */
  .video-cta { display:flex; align-items:center; gap:18px; margin:36px 0; background: var(--brand-soft);
    border:1px solid var(--line); border-radius:14px; padding:16px 20px; }
  .vc-av { display:flex; flex:0 0 auto; } .vc-av img { width:84px; height:auto; } .vc-av img + img { margin-left:-14px; }
  .vc-title { font-weight:600; font-size:17px; margin:0 0 4px; color: var(--ink); }
  .vc-text { font-size:14px; color: var(--ink-soft); margin:0 0 10px; line-height:1.65; }
  .vc-btn { display:inline-block; background: var(--brand); color:#fff; text-decoration:none; font-weight:600;
    font-size:14px; padding:9px 18px; border-radius:999px; }
  @media (max-width: 560px) { .video-cta { flex-direction:column; text-align:center; padding:16px 14px; gap:10px; }
    .vc-av img { width:76px; } }

  /* ---- テーマ別バナー ---- */
  .banner { margin: 0 0 18px; border-radius:14px; overflow:hidden; border:1px solid var(--line); background: var(--surface-2); line-height:0; }
  .banner img { width:100%; height:180px; object-fit:cover; object-position:center; display:block; }
  @media (max-width: 560px) { .banner img { height:110px; } }

  /* ---- クイズのキャラ ---- */
  .quiz-head { display:flex; align-items:center; gap:12px; margin-bottom:8px; }
  .quiz-ava { width:84px; height:auto; flex:0 0 84px; }
  .quiz-by { margin:2px 0 0; font-size:13.5px; color: var(--ink-soft); }
  .quiz-react { display:flex; align-items:center; gap:10px; margin-bottom:8px; }
  .quiz-react img { width:68px; height:auto; flex:0 0 68px; }
  .quiz-react .quiz-verdict { margin:0; font-size:16px; }
  @media (max-width: 560px) { .quiz-ava { width:68px; flex-basis:68px; } }
"""
