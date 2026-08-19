import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE = Path(__file__).parent
scan = json.loads((BASE / "data" / "scan_2026-08-19.json").read_text(encoding="utf-8"))

idx_map = {i["ticker"]: i for i in scan["indices"]}

def idx(ticker, name, unit=""):
    r = idx_map[ticker]
    delta = r["last_close"] - r["prev_close"]
    return {
        "ticker": ticker, "name": name,
        "value_text": f"{r['last_close']:,.2f}{unit}",
        "delta": delta, "pct": r["pct_change"],
    }

indices = [
    idx("^GSPC", "S&P500(前日)"),
    idx("^IXIC", "Nasdaq総合(前日)"),
    idx("^DJI", "NYダウ(前日)"),
    idx("^SOX", "SOX半導体(前日)"),
    idx("^N225", "日経平均"),
    idx("1306.T", "TOPIX(ETF)"),
    idx("^VIX", "VIX恐怖指数(前日)"),
    idx("^TNX", "米10年金利(前日)"),
]

JST = timezone(timedelta(hours=9))

edition = {
    "edition_date": "2026-08-19",
    "eyebrow": "Today's Market",
    "headline": "日経平均が3.3%安、AI関連の「電線御三家」とソフトバンクGに強い売り",
    "summary": [
        "日経平均は前日比2,231円安（-3.3%）と大幅続落。米国発の「AI相場、行き過ぎ警戒」の流れが日本にも波及した一日。",
        "とくに古河電工・フジクラ・住友電工の光ケーブル「電線御三家」やソフトバンクグループなど、AIをテーマに買われてきた銘柄がまとめて売られた。",
        "一方でメルカリは好決算・自社株買いを引き続き好感して4年7カ月ぶり高値圏。内需のディフェンシブ株（食品・化粧品・製薬など）は下げ渋った。",
    ],
    "tags": ["#AI相場", "#電線株", "#ソフトバンクG", "#利益確定売り", "#日経平均"],
    "indices": indices,
    "narrative": [
        {
            "flag": "JP",
            "title": "日本市場：AIテーマ株に「まとめ売り」",
            "paragraphs": [
                "日経平均株価は前日比<span class=\"num\">2,231円</span>安（<span class=\"num\">-3.3%</span>）の<span class=\"num\">65,229円</span>と大幅に続落しました。前日の米国市場でSOX（フィラデルフィア半導体指数）が<span class=\"num\">-5.0%</span>と急落した流れを引き継ぎ、日本でも「AIをテーマに買われてきた銘柄」への利益確定売りが加速した形です。",
                "特に目立ったのが、データセンター向け光ケーブルの需要拡大を背景に「AI関連の電線株」として買われてきた古河電気工業（<span class=\"num\">-13.5%</span>）、フジクラ（<span class=\"num\">-10.2%</span>）、住友電気工業（<span class=\"num\">-9.4%</span>）の値下がりです。3社は過去にも急ピッチな株価上昇のあとに「過熱警戒」から急落する場面が繰り返されており、値がさで値動きが荒くなりやすい銘柄として知られています。",
                "ソフトバンクグループ（<span class=\"num\">-10.4%</span>）も大きく売られました。同社はOpenAIをはじめ多数のAI関連企業に巨額出資しており、AI関連株全体が調整する局面では「AI投資の代表銘柄」として真っ先に売られやすい傾向があります。半導体設計のルネサスエレクトロニクス（<span class=\"num\">-9.3%</span>）、半導体材料のレゾナック・ホールディングス（<span class=\"num\">-8.3%</span>）にも同様に売りが波及しました。",
                "一方でメルカリ（<span class=\"num\">+5.5%</span>）は、好調な決算と上場来初の自社株買い発表を引き続き好感し4年7カ月ぶりの高値圏を維持。キッコーマン、資生堂、第一三共、協和キリンなど内需・ディフェンシブ株は総じて下げ渋りました。",
            ],
        },
        {
            "flag": "US",
            "title": "米国市場（前日）：AIメモリーと半導体に売りが集中",
            "paragraphs": [
                "前日の米国市場では、S&P500が<span class=\"num\">-0.69%</span>、ナスダック総合が<span class=\"num\">-1.33%</span>と3日続落。SOX（フィラデルフィア半導体指数）は<span class=\"num\">-4.98%</span>と大きく崩れました。背景には、ここ2週間ほど緩やかに切り上がってきた米10年国債利回り（<span class=\"num\">4.71%</span>前後）があり、「AI関連の設備投資があまりに急ピッチで進みすぎたのでは」という警戒感が広がったとみられています。",
                "個別ではマイクロン・テクノロジー（<span class=\"num\">-7.0%</span>）が代表格でした。AIメモリー関連への思惑買いが一気に巻き戻されたほか、DDR5メモリーの特許を巡ってNetlist社が米国際貿易委員会（ITC）に申し立てを行ったことも重荷となりました。インテル（<span class=\"num\">-6.6%</span>）は総額200億ドル規模に膨らんだ大型増資による希薄化懸念と、UBSによる目標株価引き下げが重なりました。",
            ],
        },
    ],
    "movers": [
        {"market": "JP", "ticker": "4385", "name": "メルカリ", "pct": 5.54, "kind": "equity",
         "reason": "好調な決算と上場来初の自社株買い発表を引き続き好感。4年7カ月ぶりの高値圏。"},
        {"market": "JP", "ticker": "2413", "name": "エムスリー", "pct": 2.01, "kind": "equity",
         "reason": "明確な材料は確認できず。相対的にAI相場との連動性が低い銘柄として資金が向かった可能性。"},
        {"market": "JP", "ticker": "4911", "name": "資生堂", "pct": 1.22, "kind": "equity",
         "reason": "内需・ディフェンシブ株として、値がさAI関連株からの資金シフト先になったとみられる。"},
        {"market": "JP", "ticker": "5801", "name": "古河電気工業", "pct": -13.53, "kind": "equity",
         "reason": "データセンター向け光ケーブル需要で「AI関連の電線株」として買われてきた反動。過熱警戒からの利益確定売りが加速。"},
        {"market": "JP", "ticker": "9984", "name": "ソフトバンクグループ", "pct": -10.43, "kind": "equity",
         "reason": "OpenAI等への巨額出資でAI投資の代表銘柄と見なされており、AI関連株全体の調整局面で真っ先に売られやすい。"},
        {"market": "JP", "ticker": "5803", "name": "フジクラ", "pct": -10.15, "kind": "equity",
         "reason": "古河電工と同じく「電線御三家」の一角。AI関連テーマ株としてまとめて売られた。"},
        {"market": "JP", "ticker": "5802", "name": "住友電気工業", "pct": -9.36, "kind": "equity",
         "reason": "同じく電線大手としてAI関連株の調整に連れ安。"},
        {"market": "JP", "ticker": "6723", "name": "ルネサスエレクトロニクス", "pct": -9.30, "kind": "equity",
         "reason": "半導体セクター全体の利益確定売りに連れ安。"},
        {"market": "JP", "ticker": "4004", "name": "レゾナック・ホールディングス", "pct": -8.31, "kind": "equity",
         "reason": "半導体材料メーカーとして、半導体株安の流れに連れ安。"},
        {"market": "US", "ticker": "LLY", "name": "エーライリリー", "pct": 3.60, "kind": "equity",
         "reason": "アルツハイマー病治療薬候補の権利取得を発表。好調な第2四半期決算・通期見通し引き上げも引き続き好感。"},
        {"market": "US", "ticker": "MU", "name": "マイクロン・テクノロジー", "pct": -7.02, "kind": "equity",
         "reason": "AIメモリー関連への思惑買いが巻き戻された。DDR5特許を巡るNetlist社のITC申し立ても重荷に。"},
        {"market": "US", "ticker": "INTC", "name": "インテル", "pct": -6.58, "kind": "equity",
         "reason": "総額200億ドル規模に膨らんだ大型増資による希薄化懸念と、UBSの目標株価引き下げが重なった。"},
        {"market": "US", "ticker": "META", "name": "メタ・プラットフォームズ", "pct": -4.45, "kind": "equity",
         "reason": "29州司法長官による「子どもの安全」訴訟が本格化。最大1.4兆ドルとも報じられる賠償リスクが意識された。"},
    ],
    "lesson_title": "なぜ「テーマ株」はまとめて上がって、まとめて下がるの？",
    "lesson_body_paragraphs": [
        "今日は電線株3社とソフトバンクグループが同時に大きく下げましたが、これは3社の業績が急に悪化したわけではなく、「AI関連株」という同じ物語（テーマ）でくくられて買われてきた銘柄群だからです。市場ではこうした銘柄を「テーマ株」「材料株」と呼びます。",
        "テーマ株は、テーマそのものへの期待が盛り上がっているときはまとめて買われ、期待が後退すると業績と関係なくまとめて売られる、という値動きをしやすいのが特徴です。個別企業の実力よりも「物語」の勢いで株価が動きやすいため、値動きが実際の業績より大きくブレやすく、上がるときも下がるときも勢いがつきやすい、と覚えておくとよいでしょう。",
    ],
    "sources_note": "データ出典：株価・指数はYahoo! Finance、金利・生産指標はFRED（セントルイス連銀）。個別銘柄の値動きの背景は各社報道（日本経済新聞、東洋経済オンライン、TipRanks、Benzinga ほか）を参照し、AIが要約しています。",
    "generated_at": datetime.now(JST).strftime("%Y-%m-%d %H:%M JST"),
}

out = BASE / "data" / "edition_2026-08-19.json"
out.write_text(json.dumps(edition, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote", out)
