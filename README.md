# なぜなぞ相場 — 日次マーケット概況の自動生成パイプライン

公開サイト: **https://goncharo55.github.io/nazenazosouba/** （GitHub Pages）

毎営業日、日本の引け直後（15:30 JST目安）に実行する。米国は前営業日分（まだ確定していないため）、
日本は当日分のデータを使う。特定銘柄の売買は推奨しない。分からない値動きは「不明」でよい。

## 全体の流れ（この順で実行する）

0. **リポジトリの取得**：クラウド実行の場合、まず https://github.com/goncharo55/nazenazosouba を
   clone（またはpull）する。このリポジトリが `data/archive.db` を含む唯一の永続化先。
   作業はこのリポジトリのルート（＝このREADMEがあるディレクトリ）で行う。
   `db.py` / `render.py` / `publish_prep.py` は標準ライブラリのみで動くので、pip installは不要。

   **⚠ ネットワーク制約（重要・実測済み）**：このリポジトリを実行するクラウドサンドボックスは、
   外部ネットワークアクセスがごく一部のドメインに限定されている（実測：`github.com` と `pypi.org` は
   到達可能、`finance.yahoo.com` / `fred.stlouisfed.org` / `stooq.com` / `google.com` 等は
   Bashからの生のcurlも、**WebFetchツールでの直接取得も**403でブロックされる。日付: 2026-08-19に確認）。
   したがって **市場データの取得は必ずWebSearchツールで行うこと**。`scan_movers.py`
   （yfinance依存）やBashでのAPI直叩き、WebFetchでの金融サイト取得は、クラウド実行では機能しない
   （ローカルのインタラクティブなClaude Codeセッションなど、ネットワーク制限のない環境でのみ動く。
   その場合は `pip install -r requirements.txt` の上で使ってよい）。

1. **WebSearchで当日の市場データを調べる**
   - 指数・レートのスナップショット（それぞれ1クエリ程度）：
     "S&P 500 close today", "NASDAQ composite close today", "Dow Jones close today",
     "Philadelphia semiconductor index SOX today", "日経平均株価 終値 本日", "TOPIX 終値 本日",
     "VIX index today", "10 year treasury yield today", "ドル円 為替レート 本日",
     "ビットコイン 価格 本日" など、必要な指標を都度検索する。
   - 値上がり/値下がりランキング：
     "S&P 500 today gainers losers", "日経225 値上がり率 値下がり率 ランキング 本日" 等。
     SlickCharts（slickcharts.com/market-movers）、Yahoo Financeのスクリーナー、株探（kabutan.jp）
     などの結果が拾えることを確認済み。ここから実際に記事化する銘柄を選ぶ
     （目安：各市場4〜9銘柄。値動きの大きさ・話題性・「他の銘柄と同じテーマで動いているか」で選ぶ）。
   - 米国・日本どちらかの市場が休場の日は、個別銘柄ランキングのクエリで有効な当日結果が出ない
     （前営業日のデータしか出てこない）ことで判別できる。休場ならその市場の個別銘柄セクションは書かず、
     24時間資産（BTC, ETH, ドル円, 原油, 金, 株価指数先物など）や前営業日のデータで記事を補う。
     **動きが小さい資産を無理に取り上げるくらいなら「今日は目立った動きはなかった」と書いてよいが、
     記事全体がスカスカにならないよう、必ずどこかの市場・資産に材料を見つけること。**
   - **検索は目安30件以内で切り上げること。** 特にTOPIXやドル円のような数字は情報源によって
     速報値・確定値・小数点以下がわずかに食い違うことがあるが、これは正常。1〜2回の検索で
     「だいたいこのくらい」という数字が分かれば十分で、完全に一致する数字を求めて何度も
     似たクエリを繰り返さない。「約2,100円安」「159円台半ば」のような概数表現で書いてよい。
     このステップ全体に使う時間の目安は5〜10分程度。

2. **値動きの理由を調べる**（引き続きWebSearchツールを使う。手順1と統合してもよい）
   - 各銘柄について `"<銘柄名> 株価 <理由 or 急落/急騰> <日付>"` のようなクエリでWebSearchする
   - 明確な材料が見つからない場合は無理に理由を作らない。
     `reason` には「明確な材料は確認できず」「〇〇株全体の値動きに連れ安（連れ高）」のように正直に書く。
     どんなに小さくても何かしら理由はあるはずなので、複数クエリを試すこと。
   - 複数銘柄が同じ理由（例：金利上昇、AI相場の調整、決算シーズン）で動いている場合は、
     その「共通テーマ」を記事の見出し・3行まとめ・きょうの用語解説のネタにする（読み応えが出る）。

3. **記事データを組み立てる**：手順1・2でWebSearchから調べた数値・理由を使って edition dict を作り、
   `data/edition_YYYY-MM-DD.json` に保存する。
   スキーマは下記「edition JSONの形」を参照。過去の `build_edition_20260819.py` が実例
   （ただしこれは初回セットアップ時にローカルで手作業で作った例で、`data/scan_*.json` を読んでいるのは
   ローカル実行時の名残。クラウド実行ではWebSearchの結果から直接dictを組み立てればよい）。

4. **DBに保存**：`python db.py save --json data/edition_YYYY-MM-DD.json`
   （SQLite: `data/archive.db`。同じ日付で再実行すると上書きされる）

5. **サイトを再生成**：`python build_site.py`
   - DBの全editionから `docs/` フォルダを丸ごと再生成する（Artifactツールは使わない）
   - `docs/index.html`（最新記事のミラー＝トップページ）、`docs/archive.html`（バックナンバー一覧）、
     `docs/glossary.html`（用語辞典）、`docs/editions/YYYY-MM-DD.html`（各日の固定リンク）を出力
   - URLの組み立ては `render.py` の `SITE_ROOT`（`/nazenazosouba`）を基準にした関数
     （`home_url()` / `archive_url()` / `glossary_url()` / `edition_url(date)`）が担当するので、
     手作業でリンクを書く必要はない
   - **公開は「pushするだけ」**：GitHub Pagesがリポジトリの `main` ブランチの `docs/` フォルダを
     配信するよう設定済みなので、以下の手順6でpushが通れば、数十秒〜数分で
     https://goncharo55.github.io/nazenazosouba/ に反映される。手動でpublishする操作は不要。

6. **用語辞典の更新（任意）**：その日の「きょうの用語解説」で新しい用語を扱った場合、
   `data/glossary_add_YYYY-MM-DD.json`（seed_glossary.jsonと同じ形式の配列）を作り、
   `python db.py add-glossary --json data/glossary_add_YYYY-MM-DD.json` で追加してから、
   もう一度 `python build_site.py` を実行する（`docs/glossary.html` に反映される）。
   既存の用語と同じtermは上書きされない（初出の説明を尊重する）ので、表現を変えたいだけなら
   このステップは不要。

7. **リポジトリへの保存＝公開**：作業後、必ず以下を実行する。
   ```
   git add -A
   git commit -m "YYYY-MM-DD分の記事を追加"
   git push
   ```
   これを忘れると、次回実行時に過去の記事やDBの内容が失われるだけでなく、**サイトも更新されない**
   （GitHub Pagesはpush済みの内容しか配信できないため）。

   **⚠ `git push` が失敗する場合**：2種類の失敗パターンが実測で確認されている。
   - `unable to access ... 403`（生の`git push`）：まず**GitHub連携のMCPツール**
     （`mcp__github__push_files` または `mcp__github__create_or_update_file`。ToolSearchで
     `select:mcp__github__push_files,mcp__github__create_or_update_file` を検索すると使える）
     を試す。`mcp__github__get_me` で認証中のGitHubユーザーを確認できる。
   - `mcp__github__push_files` でも `403 Resource not accessible by integration` になる場合：
     これは**このクラウド環境に接続されているGitHub連携（GitHub App）自体が、このリポジトリへの
     書き込み権限を持っていない**ことを意味する（2026-08-19に実測・確認済み）。README上の工夫では
     解決できない、claude.ai側の連携設定の問題。この場合は無理に何度も再試行せず、
     **PushNotificationツールでユーザーに「GitHub連携の書き込み権限を claude.ai の
     設定 → Connectors で確認してください」と通知した上で、生成済みファイルはローカルの
     working directoryに残したまま終了する**（次に人間が介入した際にpushできる状態にしておく）。

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

## オリジナリティについて（重要）

このサイトは日経新聞などの記事の丸パクリ（要約・翻訳のみ）ではない。以下を必ず守ること。

- WebSearchで得た情報は自分の言葉で書き直す。見出しやリード文をほぼそのまま言い換えただけの文章にしない。
- 単一の記事の視点をなぞるだけでなく、**複数の値動き・複数日のデータを横断して関連付ける**ことを
  「なぜなぞ相場」らしい付加価値にする。例：
  - 前日の米国の値動きと当日の日本の値動きを因果でつなぐ（例：米SOX急落→翌日の日本の半導体・AI関連株安）
  - 一見バラバラな複数の値上がり/値下がり銘柄に共通するテーマを見つけて言語化する
    （例：電線株3社＋ソフトバンクGが同時に売られた→「AIテーマ株」という共通項でくくる）
  - 指標同士の関係を説明する（金利と成長株、VIXと株価、出来高と値動きの信頼度、など）
- 事実（何が何%動いたか）はどの情報源を見ても同じだが、「どの事実を選び、どうつなげて意味づけるか」に
  このサイトの視点を出す。きょうの用語解説は、その日の値動きから逆算して「今日はこれを説明すると
  読者の理解が深まる」というテーマを選ぶこと（前もって決まった辞書的な項目を順番に消化するのではない）。
- 出典は `sources_note` に明記し、特定の記事の丸写しではなく参照であることを示す。

## 既知の注意点・今後の課題

- **公開場所はGitHub Pages**（2026-08-19〜）。以前はArtifactツールでclaude.ai上に非公開publishして
  いたが、外部から検索・アクセスできないため、GitHub Pages配信に切り替えた。`docs/`フォルダの内容が
  そのままURLに対応する（例：`docs/editions/2026-08-19.html` → `/nazenazosouba/editions/2026-08-19.html`）。
  Pages自体の設定（Settings → Pages → Source: main branch, /docs）は初回のみ人間側で行う必要がある。
- **本当の意味でのSEO（検索エンジンに見つけてもらうこと）はまだこれから**。公開URLが存在するだけでは
  Googleにインデックスされるまで時間がかかる。Google Search Consoleへのサイトマップ登録などは
  今後の課題。
- `scan_movers.py` / `sp500_list.csv` / `nikkei225_list.csv` / `requirements.txt` は、
  ネットワーク制限のないローカル環境（このリポジトリを手元にcloneしたインタラクティブなClaude Code
  セッションなど）で使うための、より精密なオプションのツール一式。クラウド自動実行では使われない
  （上記「⚠ ネットワーク制約」を参照）。ローカルで検証したい場合は
  `pip install -r requirements.txt && python scan_movers.py` で実行できる。
- 米国が休場（祝日）の日は `us_market_open=False` になるが、これは「前営業日のデータしかない」ことの
  検知でもあるので、平常運転でも米国分は基本的に「前日」の扱いになる（このプロジェクトの想定通り）。
- フォントは `fonts/*.b64.txt` にBase64化済み（Newsreader, IBM Plex Sans, IBM Plex Mono）。
  `render.py` がこれを読んでCSSに埋め込む。差し替え不要な限り触らなくてよい。
