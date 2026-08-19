# そうばノート — 日次マーケット概況の自動生成パイプライン

毎営業日、日本の引け直後（15:30 JST目安）に実行する。米国は前営業日分（まだ確定していないため）、
日本は当日分のデータを使う。特定銘柄の売買は推奨しない。分からない値動きは「不明」でよい。

## 全体の流れ（この順で実行する）

1. **スキャン**：`python scan_movers.py` （引数なし＝今日の日付で実行）
   - S&P500・日経225の全銘柄の当日騰落率と、24時間動く資産（BTC, ETH, ドル円, 原油, 金, 米株価指数先物）を取得
   - `data/scan_YYYY-MM-DD.json` に出力。標準出力にファイルパスが出る
   - `us_market_open` / `jp_market_open` を見て、その市場が休場だったかを判定できる
   - 休場だった市場は `*_movers` が空配列になる → その日はその市場の個別銘柄セクションを書かず、
     `always_on`（24時間資産）から話題を拾う。**動きが小さい資産を無理に取り上げるくらいなら
     「今日は目立った動きはなかった」と書いてよいが、記事全体がスカスカにならないよう、
     必ずどこかの市場・資産に材料を見つけること。**

2. **値動きの理由を調べる**（ここはAIが自分でやる：WebSearchツールを使う）
   - `scan_movers.py` が出す候補（上位10＋下位10）の中から、実際に記事化する銘柄を選ぶ
     （目安：各市場4〜9銘柄。値動きの大きさ・話題性・「他の銘柄と同じテーマで動いているか」で選ぶ）
   - 各銘柄について `"<銘柄名> 株価 <理由 or 急落/急騰> <日付>"` のようなクエリでWebSearchする
   - 明確な材料が見つからない場合は無理に理由を作らない。
     `reason` には「明確な材料は確認できず」「〇〇株全体の値動きに連れ安（連れ高）」のように正直に書く。
     どんなに小さくても何かしら理由はあるはずなので、複数クエリを試すこと。
   - 複数銘柄が同じ理由（例：金利上昇、AI相場の調整、決算シーズン）で動いている場合は、
     その「共通テーマ」を記事の見出し・3行まとめ・きょうの用語解説のネタにする（読み応えが出る）。

3. **記事データを組み立てる**：`data/scan_YYYY-MM-DD.json` の数値と、手順2で調べた理由を使って
   edition dict を作り、`data/edition_YYYY-MM-DD.json` に保存する。
   スキーマは下記「edition JSONの形」を参照。過去の `build_edition_20260819.py` が実例。

4. **DBに保存**：`python db.py save --json data/edition_YYYY-MM-DD.json`
   （SQLite: `data/archive.db`。同じ日付で再実行すると上書きされる）

5. **HTML生成**：`python publish_prep.py --date YYYY-MM-DD`
   - `edition_YYYY-MM-DD.html`（当日記事）と `archive.html`（バックナンバー一覧）を生成
   - `config.json` の `archive_url` を自動で読み込んでクロスリンクする

6. **公開**：Artifactツールで2つ publish する
   - `edition_YYYY-MM-DD.html` → 新規publish（file_pathが毎回変わるので必ず新しいURLになる）
   - 公開後に返ってきたURLを `python db.py set-url --date YYYY-MM-DD --url "https://..."` でDBに保存
   - `python publish_prep.py --date YYYY-MM-DD` を再実行して archive.html を作り直す
     （これで今日の記事がバックナンバー一覧に載る）
   - `archive.html` を Artifactツールで publish する。**2回目以降は同じ `archive.html` の file_path で
     publishすれば同じURLが維持される（`config.json` に保存済みのURLと一致するはず）**
   - 当日記事も、archive_urlが確定した後にもう一度 `publish_prep.py` → publish し直すと、
     記事側からバックナンバーへのリンクも正しく入る（初回セットアップ時のみ必要な手順。
     2日目以降は既に `config.json` にarchive_urlがあるので1回のpublishで済む）

## edition JSONの形

```json
{
  "edition_date": "2026-08-19",
  "eyebrow": "Today's Market",
  "headline": "見出し（1行、その日のテーマを一言で）",
  "summary": ["3行まとめの1行目", "2行目", "3行目"],
  "tags": ["#タグ1", "#タグ2"],
  "indices": [
    {"ticker": "^GSPC", "name": "S&P500", "value_text": "7,691.76", "delta": -53.30, "pct": -0.69}
  ],
  "narrative": [
    {"flag": "JP", "title": "日本市場：...", "paragraphs": ["<p>の中身。<span class=\"num\">数字</span>のように強調可"]},
    {"flag": "US", "title": "米国市場（前日）：...", "paragraphs": ["..."]}
  ],
  "movers": [
    {"market": "JP", "ticker": "4385", "name": "メルカリ", "pct": 5.54, "kind": "equity", "reason": "..."}
  ],
  "lesson_title": "きょうの用語解説のタイトル",
  "lesson_body_paragraphs": ["段落1", "段落2"],
  "sources_note": "データ出典の一文",
  "generated_at": "2026-08-19 15:35 JST"
}
```

- `narrative` は配列なので、市場が休場の日は該当セクションを省いてよい。
  代わりに `flag: "24H"` などで為替・暗号資産のセクションを足してもよい。
- `movers` の `market` は `"JP"` / `"US"` / `"GLOBAL"`（24時間資産用）。
  `render.py` の `MARKET_LABELS` がパネルの見出しに変換する。

## 既知の注意点・今後の課題

- **これはSEO対策にはまだならない**：Artifactはデフォルトで非公開（作者以外は見えない）で、
  Googleなどの検索エンジンにクロールされない。本当にSEOを狙うなら、将来的に静的サイト（例：GitHub Pages,
  Vercel等）に配信する仕組みに切り替える必要がある。今の仕組みは「毎日自動でコンテンツを溜める土台」
  として割り切っている。
- ウォッチリストの銘柄名・ticker対応表は `sp500_list.csv`（英語Wikipedia）と `nikkei225_list.csv`
  （日本語Wikipedia）から一度だけ生成したもの。銘柄の入れ替え（S&P500の構成変更など）に追従するには
  定期的に再生成が必要（`generate_universe.py` は未作成、必要になったら `scan_movers.py` の
  `load_universe()` と同じロジックで作る）。
- 米国が休場（祝日）の日は `us_market_open=False` になるが、これは「前営業日のデータしかない」ことの
  検知でもあるので、平常運転でも米国分は基本的に「前日」の扱いになる（このプロジェクトの想定通り）。
- フォントは `fonts/*.b64.txt` にBase64化済み（Newsreader, IBM Plex Sans, IBM Plex Mono）。
  `render.py` がこれを読んでCSSに埋め込む。差し替え不要な限り触らなくてよい。
