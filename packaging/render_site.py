"""Render the static GitHub Pages site and five README editions from shared copy."""

from pathlib import Path
import json
import html
import hashlib

R = Path(__file__).resolve().parents[1]
DATA = json.loads((R / "site/content.json").read_text())
GH = "https://github.com/THXel/Boshy-Randomizer"
GAME = "https://grynsoft.com/site/game/i-wanna-be-the-boshy"


def e(s):
    return html.escape(s, quote=True)


def render(lang, d):
    prefix = "" if lang == "en" else "../../"
    assets = lambda p: prefix + p
    versioned = (
        lambda p: assets(p)
        + "?v="
        + hashlib.sha256((R / p).read_bytes()).hexdigest()[:12]
    )
    w = d["web"]
    updates = json.loads((R / "site/updates.json").read_text())
    preview = updates["preview"]
    preview_copy = preview["locales"][lang]
    presentation = preview_copy["presentation"]
    languages = "".join(
        f'<a href="{prefix+("index.html" if code=="en" else "site/"+code+"/index.html")}" lang="{code}" hreflang="{code}" {"aria-current=\"page\"" if code==lang else ""}>{e(v["name"])}</a>'
        for code, v in DATA.items()
    )
    nav = "".join(
        f'<a href="#{k}">{e(v)}</a>'
        for k, v in zip(("modes", "features", "gallery", "download"), d["nav"])
    )
    nav = f'<a href="#development">{e(presentation["nav"])}</a>' + nav
    buttons = f'<a class="button primary" href="#download">Windows · {e(preview_copy["soon"])}</a><a class="button secondary" href="#download">Linux · {e(preview_copy["soon"])}</a>'

    def mascot(color):
        file, alt, size = (
            ("Custom/boshy.png", "Boshy", 384)
            if color == "yellow"
            else ("Custom/trophies/Dark%20Boshy.png", "Dark Boshy", 32)
        )
        return f'<div class="mascot mascot-{color}"><div class="mascot-art"><img src="{assets(file)}" alt="{alt}" width="{size}" height="{size}"></div></div>'

    advice = "".join(
        f'<li class="mode-advice" id="mode-{i}"><p class="mode-intent">{e(label)}</p><h4>{e(n)}</h4><p class="mode-description">{e(body)}</p></li>'
        for i, (label, (n, tag, body)) in enumerate(zip(w["choices"], d["modes"]))
    )
    features = "".join(
        f'<article><span class="feature-mark">{mark}</span><h3>{e(n)}</h3><p>{e(body)}</p></article>'
        for mark, (n, body) in zip(("↗", "✦", "#", "III", "◷", "★"), d["features"])
    )
    hacks = "".join(f"<li>{e(x)}</li>" for x in d["hacks"])
    controls = "".join(f"<li>{e(x)}</li>" for x in d["controls"])
    installation = "".join(
        f"<article><h4>{platform}</h4><ol>"
        + "".join(
            f"<li><strong>{e(title)}</strong><p>{e(body)}</p></li>"
            for title, body in presentation[key]
        )
        + "</ol></article>"
        for platform, key in (("Windows", "windowssteps"), ("Linux", "linuxsteps"))
    )
    current_screenshots = "".join(
        f'<figure><a href="{assets(base + ".gif")}" data-gallery-index="{index}" '
        f'data-video="{assets(base + ".mp4")}" data-audio="false" data-poster="{assets(base + ".png")}" data-caption="{e(caption)}">'
        f'<picture><source media="(prefers-reduced-motion: reduce)" srcset="{assets(base + ".png")}">'
        f'<img src="{assets(base + ".png")}" alt="{e(caption)}" loading="lazy" width="640" height="480"></picture>'
        f'<span class="zoom-mark" aria-hidden="true">▶</span></a>'
        f'<figcaption>{e(caption)}<span class="media-links"><a href="{assets(base + ".gif")}">GIF</a></span></figcaption></figure>'
        for index, (base, caption) in enumerate(
            zip(
                (
                    "site/media/run-menu",
                    "site/media/target-select",
                    "site/media/options-language",
                ),
                presentation["captions"],
            )
        )
    )
    faq = "".join(
        f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>"
        for q, a in d["faq"]
    )
    gallery = ""
    previews = [
        (
            "site/media/death-undertale.gif",
            "site/media/death-undertale.png",
            "site/media/death-undertale.mp4",
            True,
        ),
        (
            "docs/media/death-kamilia3.gif",
            "site/media/death-kamilia3-poster.webp",
            "site/media/death-kamilia3.mp4",
            True,
        ),
        (
            "docs/media/death-wannafest22.gif",
            "site/media/death-wannafest22-poster.webp",
            "site/media/death-wannafest22.mp4",
            True,
        ),
    ]
    for i, ((original, poster, video, audio), caption) in enumerate(
        zip(previews, d["galleryCaptions"])
    ):
        downloads = f'<span class="media-links"><a href="{assets(original)}">GIF</a>'
        if audio:
            downloads += f'<a href="{assets(video)}">{e(w["soundvideo"])}</a>'
        downloads += "</span>"
        picture = f'<img src="{assets(poster)}" alt="{e(caption)}" loading="lazy" width="640" height="480">'
        if not audio:
            picture = f'<picture><source media="(prefers-reduced-motion: reduce)" srcset="{assets(poster)}"><img src="{assets(original)}" alt="{e(caption)}" loading="lazy" width="640" height="480"></picture>'
        gallery += f'<figure><a href="{assets(video if audio else original)}" data-gallery-index="{i + 3}" data-video="{assets(video)}" data-audio="{str(audio).lower()}" data-poster="{assets(poster)}" data-caption="{e(caption)}">{picture}<span class="zoom-mark" aria-hidden="true">▶</span></a><figcaption>{e(caption)}{downloads}</figcaption></figure>'
    issue = GH + "/issues"
    text = f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{e(d['intro'])}"><meta name="theme-color" content="#101411"><meta property="og:title" content="Boshy Randomizer — {e(d['title'])}"><meta property="og:description" content="{e(d['tagline'])}"><meta property="og:image" content="https://thxel.github.io/Boshy-Randomizer/Custom/boshy_randomizer.png"><title>Boshy Randomizer — {e(d['title'])}</title><link rel="stylesheet" href="{versioned('site/style.css')}"><link rel="icon" href="{assets('Custom/rando_icon.ico')}"><script src="{versioned('site/app.js')}" defer></script></head><body>
<a class="skip" href="#main">{e(d['nav'][1])}</a>
<header class="header"><a class="brand" href="#"><img src="{assets('Custom/boshy_randomizer.png')}" alt="Boshy Randomizer" width="180" height="72"></a><nav aria-label="Main">{nav}</nav><a class="github" href="{GH}">GitHub ↗</a></header><nav class="language-top wrap languages" aria-label="Language">{languages}</nav>
<main id="main">
<section class="hero wrap"><div class="hero-copy"><div class="eyebrow">FAN PROJECT · WINDOWS + LINUX</div><h1>{e(d['title'])}</h1><p class="tagline">{e(d['tagline'])}</p><p class="intro">{e(d['intro'])}</p><p class="release-label">{e(preview_copy["download"])}</p><div class="actions">{buttons}</div><p class="preview-link"><a href="#development">{e(preview_copy["status"])} →</a></p><p class="fine">{e(d['game'])}</p><p class="original-game"><a href="{GAME}">{e(d['gameDownload'])} ↗</a></p><a class="text-link" href="#quickstart">{e(w['quick'])} →</a></div>
<div class="hero-cast">{mascot('yellow')}</div>
<div class="hero-media motion-player"><div class="screen-bar"><span>● ● ●</span><span>I WANNA BE THE BOSHY</span></div><video class="hero-video" width="880" height="660" muted loop playsinline preload="metadata" poster="{assets('site/media/worlds-sprites.png')}" aria-label="{e(d['showcase']['worlds'])}"><source src="{assets('site/media/worlds-sprites.mp4')}" type="video/mp4"></video><div class="screen-bottom"><span>RANDOMIZER EDITION</span><button type="button" class="media-toggle enhanced-only" data-play="{e(w['play'])}" data-pause="{e(w['pause'])}">{e(w['play'])}</button></div></div></section>
<div class="ribbon"><span>5 MODES</span><span>3 SAVE SLOTS</span><span>SHARE YOUR SEED</span><span>MAKE IT YOUR RUN</span></div>
<section id="development" class="wrap section development" aria-labelledby="development-title"><div class="section-heading"><span class="eyebrow">{e(preview_copy['status'])}</span><h2 id="development-title">{e(preview_copy['title'])}</h2><p class="preview-notice">{e(preview_copy['notice'])}</p></div><div class="current-screenshots"><p>{e(presentation['shotnote'])}</p><div class="gallery">{current_screenshots}</div></div></section>
<section id="modes" class="wrap section"><div class="section-heading"><span class="eyebrow">01 / PLAY</span><h2>{e(d['play'])}</h2></div>
<div class="mode-picker"><h3>{e(w['chooser'])}</h3><ol class="mode-recommendations">{advice}</ol></div>
</section>
<section id="features" class="wrap section"><div class="section-heading"><span class="eyebrow">02 / REMIX</span><h2>{e(d['featuresTitle'])}</h2></div><div class="features">{features}</div></section>
<section class="wrap section tracker-showcase"><div><span class="eyebrow">LIVE TRACKER</span><h2>{e(d['showcase']['trackerTitle'])}</h2><p>{e(d['showcase']['tracker'])}</p></div><a href="{assets('site/media/live-tracker.png')}" data-gallery-index="6" data-caption="{e(d['showcase']['trackerTitle'])}"><img src="{assets('site/media/live-tracker.png')}" alt="{e(d['showcase']['trackerTitle'])}" loading="lazy" width="1560" height="880"></a></section>
<section class="spotlight"><div class="wrap split"><div><span class="eyebrow">NEW LOOK · SAME BOSHY</span><h2>{e(d['visualTitle'])}</h2><p>{e(d['visual'])}</p></div><div class="audio"><h3>{e(d['shotsTitle'])}</h3><p>{e(d['shots'])}</p><p>{e(d['music'])}</p></div></div></section>
<section class="wrap section hacks"><div class="section-heading"><span class="eyebrow">03 / ADVANCED</span><h2>{e(d['hacksTitle'])}</h2><p>{e(d['hacksIntro'])}</p></div><ul class="chips">{hacks}</ul><div class="comfort"><h3>{e(d['controlsTitle'])}</h3><ul>{controls}</ul></div></section>
<section id="gallery" class="wrap section"><div class="section-heading"><span class="eyebrow">04 / IN GAME</span><h2>{e(d['galleryTitle'])}</h2><p>{e(w['galleryhelp'])}</p></div><div class="gallery">{gallery}</div></section>
<section id="download" class="download"><div class="wrap"><div class="download-heading"><div><span class="eyebrow">05 / YOUR NEXT RUN</span><h2>{e(d['download'])}</h2><p class="release-label">{e(preview_copy["download"])}</p></div>{mascot('dark')}</div><div class="download-grid"><article><h3>Windows</h3><p>{e(d['preview'])}</p><span class="button primary coming-soon">{e(preview_copy["soon"])}</span></article><article><h3>Linux</h3><p>{e(d['linuxnote'])}</p><span class="button secondary coming-soon">{e(preview_copy["soon"])}</span></article></div><p class="fine">{e(d['game'])}</p><p class="original-game"><a href="{GAME}">{e(d['gameDownload'])} ↗</a></p><h3 id="quickstart" class="start-title">{e(w['quick'])}</h3><p class="install-note">{e(presentation["installnote"])}</p><div class="install-guides">{installation}</div><p class="preserve">{e(d['preserve'])}</p></div></section>
<section class="wrap section faq"><div><span class="eyebrow">06 / SUPPORT</span><h2>{e(d['faqTitle'])}</h2></div><div>{faq}</div></section>
<section class="wrap feedback"><div><h2>{e(w['feedback'])}</h2><p>{e(w['feedbackintro'])}</p><p>{e(w['debug'])}</p><a class="button primary" href="{issue}">{e(w['report'])} ↗</a></div><div class="report-template"><label for="report-template">{e(w['copy'])}</label><textarea id="report-template" rows="12" readonly spellcheck="false">{e(w['template'].replace(chr(92)+'n',chr(10)))}</textarea><button type="button" class="button secondary enhanced-only" id="copy-report" data-success="{e(w['copied'])}" data-fallback="{e(w['copyfallback'])}">{e(w['copy'])}</button><p id="copy-status" role="status"></p></div></section>
</main>
<dialog class="gallery-dialog" aria-labelledby="gallery-caption"><div class="dialog-bar"><span id="gallery-count"></span><button type="button" data-gallery-close>{e(w['close'])} ×</button></div><img class="gallery-full" alt="" hidden><video class="gallery-full" controls muted loop playsinline hidden></video><h3 id="gallery-caption"></h3><div class="dialog-navigation"><button type="button" data-gallery-prev>← {e(w['previous'])}</button><button type="button" data-gallery-next>{e(w['next'])} →</button></div></dialog>
<footer class="wrap"><img src="{assets('Custom/boshy_randomizer.png')}" alt="Boshy Randomizer" width="150" height="60"><p>{e(d['footer'])}</p><div class="languages" aria-label="Language">{languages}</div><div class="footer-links"><a href="{issue}">{e(d['support'])}</a><a href="#development">{e(presentation["nav"])}</a></div></footer></body></html>"""
    target = R / "index.html" if lang == "en" else R / "site" / lang / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text + "\n")


def readme(lang, d, root=False):
    pre = "" if root else "../"
    suffix = {"en": "EN", "de": "DE", "ru": "RU", "es": "ES", "ja": "JP"}
    langs = " · ".join(
        f'[{v["name"]}]({"README/" if root else ""}README_{suffix[k]}.md)'
        for k, v in DATA.items()
    )
    site = "https://thxel.github.io/Boshy-Randomizer/" + (
        "" if lang == "en" else "site/" + lang + "/"
    )
    preview = json.loads((R / "site/updates.json").read_text())["preview"]["locales"][
        lang
    ]
    c = d["showcase"]
    s = f"""<div align="center">

<img src="{pre}Custom/boshy_randomizer.png" alt="Boshy Randomizer" width="420">

# {d['title']}

**{d['tagline']}**

{langs}

[Website]({site})

</div>

{d['intro']}

> **{preview['download']}**
>
> {preview['notice']}

![{c['worlds']}]({pre}site/media/worlds-sprites.gif)

## {d['play']}

| | |
| --- | --- |
"""
    s += "".join(f"| **{n}** | {body} |\n" for n, tag, body in d["modes"])
    s += f"\n## {d['featuresTitle']}\n\n"
    s += "".join(f"- **{title}:** {body}\n" for title, body in d["features"])
    for title, base in (
        (c['captions'][0], 'run-menu'),
        (c['target'], 'target-select'),
        (c['options'], 'options-language'),
    ):
        s += f"\n## {title}\n\n[![{title}]({pre}site/media/{base}.gif)]({site}#development)\n"
    s += f"\n## {c['trackerTitle']}\n\n{c['tracker']}\n\n![{c['trackerTitle']}]({pre}site/media/live-tracker.png)\n"
    s += f"\n## {d['visualTitle']}\n\n{d['visual']}\n\n{d['shots']} {d['music']}\n\n[![{c['death']}]({pre}site/media/death-undertale.gif)]({site}#gallery)\n\n[{d['web']['soundvideo']}](https://thxel.github.io/Boshy-Randomizer/site/media/death-undertale.mp4) · [{d['galleryTitle']}]({site}#gallery)\n"
    s += (
        f"\n## {d['hacksTitle']}\n\n{d['hacksIntro']}\n\n"
        + " · ".join(d['hacks'])
        + "\n"
    )
    s += f"\n## {d['controlsTitle']}\n\n" + " · ".join(d['controls']) + "\n"
    s += f"\n## {d['download']}\n\n**Windows (.exe) · Linux (.deb) — {preview['soon']}**\n\n{d['game']} [{d['gameDownload']}]({GAME})\n\n{d['preserve']}\n"
    s += f"\n## {d['faqTitle']}\n\n"
    for q, answer in d['faq']:
        s += f"<details>\n<summary>{q}</summary>\n\n{answer}\n\n</details>\n\n"
    s += f"---\n\n{d['footer']}\n\n[{d['support']}]({GH}/issues) · [Credits]({pre}Custom/License.txt)\n"
    target = (
        R / "README.md" if root else R / "README" / ("README_" + suffix[lang] + ".md")
    )
    target.write_text(s)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-only", action="store_true")
    args = parser.parse_args()
    for lang, d in DATA.items():
        render(lang, d)
        if not args.site_only:
            readme(lang, d)
    if not args.site_only:
        readme("en", DATA["en"], True)
