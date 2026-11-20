"""サイトの案内ページ：「サイトについて」と「お問い合わせ」。build_site.py から呼ばれる。

運営者個人の情報や売買の手法は載せない（ユーザーの方針）。
サイトの目的・作り方・編集方針・訂正の方針・免責だけを書く。
"""
from pathlib import Path

import render
from render import esc, masthead, page_shell, SITE_NAME_A, SITE_NAME_B

NAME = SITE_NAME_A + SITE_NAME_B


def about_url() -> str:
    return f"{render.SITE_ROOT}/about.html"


def contact_url() -> str:
    return f"{render.SITE_ROOT}/contact.html"


def _contact_line() -> str:
    if render.CONTACT_EMAIL:
        e = esc(render.CONTACT_EMAIL)
        return f'<p class="contact-mail"><a href="mailto:{e}">{e}</a></p>'
    return "<p>（お問い合わせ用のメールアドレスを準備中です。近日中にこちらに掲載します。）</p>"


def _footer() -> str:
    return f"""<footer class="footer">
    <p>{NAME}は、公開データと報道をもとに毎営業日まとめている市場概況です。特定の銘柄の売買を推奨するものではありません。</p>
  </footer>"""


def build_about_html() -> str:
    a_url, g_url = render.archive_url(), render.glossary_url()
    yt = (f'<li><strong>週刊なぜなぞ相場（YouTube）</strong>：1週間の値動きを、ずんだもんと四国めたんの掛け合いでまとめる動画です。毎週木曜〜金曜に公開しています。'
          f'{" <a href=\"" + esc(render.YOUTUBE_URL) + "\" target=\"_blank\" rel=\"noopener\">チャンネルを見る</a>" if render.YOUTUBE_URL else ""}</li>')
    body = f"""
  {masthead("サイトについて", a_url, g_url, page="about")}

  <section class="hero">
    <p class="eyebrow">About</p>
    <h1 class="headline">{NAME}について</h1>
    <p style="color:var(--ink-soft); max-width:66ch;">{esc(render.TAGLINE)}</p>
  </section>

  <section class="article">
    <h3>このサイトの目的</h3>
    <p>{NAME}は、株・為替・金・原油・暗号資産などの値動きについて、「なぜ上がったのか」「なぜ下がったのか」を、投資をはじめたばかりの人にもわかる言葉で解説するサイトです。ニュースの見出しだけでは分かりにくい値動きの理由を、データと報道をつき合わせて整理します。理由がはっきりしない値動きは、無理にこじつけず「不明」と書きます。</p>

    <h3>載せているもの</h3>
    <ul>
      <li><strong>毎日の記事</strong>：東京市場の引け後に、日米の株価指数・為替・金・原油・暗号資産などの動きと、大きく動いた銘柄の背景をまとめています。<a href="{esc(a_url)}">過去の記事一覧</a></li>
      <li><strong>金融用語辞典</strong>：記事に出てきた用語を、たとえ話を交えてやさしく解説しています。<a href="{esc(g_url)}">金融用語辞典</a></li>
      <li><strong>今週の実践</strong>：この番組の口座で実際に行った売買の記録です（売買した週だけ）。<a href="{esc(render.SITE_ROOT)}/practice/">今週の実践</a></li>
      {yt}
    </ul>

    <h3>記事の作り方</h3>
    <p>株価・為替などの数値は、Yahoo Finance などの公開データから毎日決まった時刻に取得し、サイト専用のデータとして保存しています。記事中の数値はすべてこのデータから引いており、文章を書いたあとに、記事の数値とデータが一致しているかを機械的に照合しています。</p>
    <p>値動きの理由は、各社の適時開示・決算資料や、報道機関のニュースを参照して書いています。参照した情報源は、各記事の末尾に記載しています。文章の作成にはAI（人工知能）を活用していますが、数値の照合と情報源の確認を経てから公開しています。</p>

    <h3>編集の方針</h3>
    <ul>
      <li>特定の銘柄・金融商品の売買をすすめることはしません。</li>
      <li>うわさや出どころの分からない情報は、事実として扱いません。報道どうしが食い違うときは、両方を並べたうえで一次情報（会社の公式発表など）の確認をうながします。</li>
      <li>専門用語には、できるだけ用語辞典へのリンクや言い換えを添えます。</li>
    </ul>

    <h3>誤りを見つけたら</h3>
    <p>数値や内容の誤りに気づいた場合は、確認のうえで記事を訂正します。お気づきの点があれば、<a href="{esc(contact_url())}">お問い合わせ</a>からお知らせください。</p>

    <h3>免責事項</h3>
    <p>当サイトの情報は、金融・経済への理解を深めていただくための情報提供を目的としたものです。内容の正確性には配慮していますが、誤りを含む可能性があり、その正確性・完全性を保証するものではありません。投資に関する最終的な判断は、ご自身の責任で行ってください。当サイトの情報を利用したことによって生じた損害について、当サイトは責任を負いかねます。詳しくは<a href="{esc(render.privacy_url())}">プライバシーポリシー・免責事項</a>をご覧ください。</p>
  </section>

  {_footer()}
"""
    return page_shell(f"{NAME}について — 目的・記事の作り方・編集方針", body,
                      description=f"{NAME}は、株・為替・金・暗号資産の値動きの理由をやさしく解説するサイトです。記事の作り方、編集の方針、免責事項を説明しています。",
                      standalone=True, canonical_path=about_url())


def build_contact_html() -> str:
    a_url, g_url = render.archive_url(), render.glossary_url()
    body = f"""
  {masthead("お問い合わせ", a_url, g_url, page="contact")}

  <section class="hero">
    <p class="eyebrow">Contact</p>
    <h1 class="headline">お問い合わせ</h1>
  </section>

  <section class="article">
    <p>{NAME}へのご意見・ご感想、記事の誤りのご指摘、その他のお問い合わせは、下記のメールアドレスまでお送りください。</p>
    {_contact_line()}
    <h3>お願い</h3>
    <ul>
      <li>個別の銘柄の売買や、投資の判断についてのご相談にはお答えできません。</li>
      <li>内容を確認のうえ、必要に応じて返信いたします。返信までお時間をいただく場合や、すべてのお問い合わせにはお答えできない場合があります。</li>
      <li>いただいた個人情報は、お問い合わせへの対応以外には使用しません。詳しくは<a href="{esc(render.privacy_url())}">プライバシーポリシー</a>をご覧ください。</li>
    </ul>
  </section>

  {_footer()}
"""
    return page_shell(f"お問い合わせ — {NAME}", body,
                      description=f"{NAME}へのお問い合わせ（ご意見・記事の誤りのご指摘など）はこちらから。",
                      standalone=True, canonical_path=contact_url())


def build_all(docs: Path) -> list[str]:
    (docs / "about.html").write_text(build_about_html(), encoding="utf-8")
    (docs / "contact.html").write_text(build_contact_html(), encoding="utf-8")
    # AdSense の販売者確認（審査前から置いておいてよい）
    (docs / "ads.txt").write_text(
        f"google.com, {render.ADSENSE_CLIENT.replace('ca-', '')}, DIRECT, f08c47fec0942fa0\n", encoding="utf-8")
    print("wrote about.html, contact.html, ads.txt")
    return [render.SITE_PUBLIC_URL + about_url(), render.SITE_PUBLIC_URL + contact_url()]
