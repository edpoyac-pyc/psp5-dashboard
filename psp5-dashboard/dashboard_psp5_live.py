#!/usr/bin/env python3
"""Dashboard PSP5 (Amundi PEA S&P 500) mis à jour depuis justETF.

Usage :
    python dashboard_psp5_live.py            # télécharge justETF puis écrit dashboard_psp5.html
    python dashboard_psp5_live.py --offline  # utilise les valeurs de secours (test sans internet)

Aucune bibliothèque externe : Python 3.8+ suffit.
Planification hebdo : cron (Linux/Mac) ou Planificateur de tâches (Windows).
"""
import html as H, math, re, sys, urllib.request
from datetime import datetime

URL = "https://www.justetf.com/fr/etf-profile.html?isin=FR0011871128"
OUT = "dashboard_psp5.html"

# Valeurs de secours (relevé du 27/11/2026) si un champ n'est pas retrouvé.
D = dict(ytd=17.41, m1=0.71, m3=4.62, m6=12.49, y1=18.13, y3=76.12, y5=83.86,
         a2022=-12.99, a2023=21.66, a2024=32.86, a2025=3.43,
         vol1=12.23, vol3=15.33, vol5=16.92, rr1=1.48, rr3=1.35, rr5=0.77,
         dd1=-7.49, dd3=-22.42, dd5=-22.42, ddmax=-33.57,
         ter=0.12, aum=1253.0, top10=37.81, tech=45.20, fin=13.69, sante=9.12,
         tops="NVIDIA 7,94 % · Apple 7,08 % · Microsoft 5,75 %")


def num(s):
    s = s.replace("\u2212", "-").replace("\xa0", "").replace(" ", "").replace("+", "").replace(",", ".")
    return float(s)


def fr(v, sign=False, d=2):
    t = f"{abs(v):,.{d}f}".replace(",", " ").replace(".", ",")
    return ("+" if v > 0 and sign else "\u2212" if v < 0 else "") + t


NUM = r"([+\-\u2212]?\d[\d\s]*,\d+)"


def fetch():
    req = urllib.request.Request(URL, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
        "Accept-Language": "fr-FR,fr;q=0.9"})
    raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    return re.sub(r"\s+", " ", H.unescape(re.sub(r"<[^>]+>", " ", raw)))


def parse(text):
    d, missing = dict(D), []
    def g(key, pat, pct=True):
        m = re.search(pat + r"\s*\|?\s*" + NUM + (r"\s*%" if pct else ""), text)
        if m:
            d[key] = num(m.group(1))
        else:
            missing.append(key)
    for k, lab in [("ytd", "Année en cours"), ("m1", r"\b1 mois"), ("m3", r"\b3 mois"), ("m6", r"\b6 mois"),
                   ("y1", r"\b1 an"), ("y3", r"\b3 ans"), ("y5", r"\b5 ans")]:
        g(k, lab)
    for y in (2022, 2023, 2024, 2025):
        g(f"a{y}", rf"\b{y}")
    for k, lab in [("vol1", "Volatilité 1 an"), ("vol3", "Volatilité 3 ans"), ("vol5", "Volatilité 5 ans"),
                   ("dd1", "Perte maximale sur 1 an"), ("dd3", "Perte maximale sur 3 ans"),
                   ("dd5", "Perte maximale sur 5 ans"), ("ddmax", "Perte maximale depuis le lancement")]:
        g(k, lab)
    for k, lab in [("rr1", "1 an"), ("rr3", "3 ans"), ("rr5", "5 ans")]:
        g(k, f"Ratio rendement/risque sur {lab}", pct=False)
    g("ter", r"TER\s*\|?\s*(?:[^\d]{0,40})?(?=\d)", ) if False else None
    m = re.search(r"TER\s*" + NUM + r"\s*% p\.a", text)
    if m: d["ter"] = num(m.group(1))
    else: missing.append("ter")
    m = re.search(r"Taille du fonds\s*EUR\s*([\d\s]+?)\s*M", text)
    if m: d["aum"] = float(re.sub(r"\s", "", m.group(1)))
    else: missing.append("aum")
    m = re.search(r"10 principales positions sur \d+ au total " + NUM + r"\s*%", text)
    if m: d["top10"] = num(m.group(1))
    else: missing.append("top10")
    g("tech", "Technologie"); g("fin", "Finance"); g("sante", "Soins de santé")
    try:
        sec = text.split("Les 10 principales positions", 1)[1].split("Pays", 1)[0]
        pairs = re.findall(r"([A-Z][A-Za-z0-9.,&' ]+?)\s+(\d{1,2},\d{2})\s*%", sec.split("au total", 1)[1])
        if pairs:
            d["tops"] = " · ".join(f"{n.strip()} {p} %" for n, p in pairs[:3])
    except Exception:
        missing.append("tops")
    return d, missing


def signals(d):
    s = []
    if d["m3"] > 0 and d["m6"] > 0: s.append(("g", "Tendance haussière", f"{fr(d['m3'],True)} % sur 3 mois, {fr(d['m6'],True)} % sur 6 mois : le marché progresse, sans courir après la hausse."))
    elif d["m3"] < 0 and d["m6"] < 0: s.append(("r", "Tendance baissière", f"{fr(d['m3'],True)} % sur 3 mois, {fr(d['m6'],True)} % sur 6 mois : attendre une stabilisation ou entrer par petites tranches."))
    else: s.append(("o", "Tendance mitigée", f"{fr(d['m3'],True)} % sur 3 mois, {fr(d['m6'],True)} % sur 6 mois : les périodes se contredisent."))
    ratio = d["vol1"] / d["vol3"]
    if d["vol1"] > 20: s.append(("r", "Volatilité tendue", f"{fr(d['vol1'])} % sur 1 an : variations fortes, limiter chaque tranche."))
    elif ratio > 1.15: s.append(("o", "Volatilité en hausse", f"{fr(d['vol1'])} % sur 1 an contre {fr(d['vol3'])} % sur 3 ans : le marché s'agite."))
    elif ratio < 0.85: s.append(("g", "Volatilité calme", f"{fr(d['vol1'])} % sur 1 an contre {fr(d['vol3'])} % sur 3 ans : bonnes conditions d'exécution."))
    else: s.append(("g", "Volatilité normale", f"{fr(d['vol1'])} % sur 1 an, proche de la moyenne sur 3 ans ({fr(d['vol3'])} %)."))
    if d["ytd"] > 15: s.append(("o", "Niveau élevé", f"{fr(d['ytd'],True)} % depuis janvier : un achat en un bloc est plus exposé à un repli."))
    elif d["ytd"] < 0: s.append(("g", "Marché en repli", f"{fr(d['ytd'],True)} % depuis janvier : zone propice aux renforts progressifs."))
    else: s.append(("g", "Niveau modéré", f"{fr(d['ytd'],True)} % depuis janvier : rien d'excessif."))
    cols = [c for c, _, _ in s]
    if "r" in cols: v = ("r", "Prudence", "Investir par petites tranches et attendre des signes de stabilisation.")
    elif "o" in cols: v = ("o", "Zone neutre", "Versement régulier ; pour une grosse somme, 3 tranches et garder les suivantes pour un repli.")
    else: v = ("g", "Zone favorable", "Le versement régulier est particulièrement pertinent ; une tranche supplémentaire est envisageable.")
    return s, v


def bars(rows, mx):
    out = ""
    for n, x in rows:
        w = min(100, abs(x) / mx * 100)
        out += (f'<div class="row"><span class="n">{n}</span><span class="b"><i class="{"neg" if x<0 else ""}" style="width:{w:.0f}%"></i></span>'
                f'<span class="p {"dn" if x<0 else "up"}">{fr(x,True)} %</span></div>')
    return out


def build(d, missing, live):
    sig, ver = signals(d)
    sd = d["vol1"] / math.sqrt(52)
    sigh = "".join(f'<div><span class="dot d{c}"></span><b>{t}</b>{x}</div>' for c, t, x in sig)
    perf = bars([("Année en cours", d["ytd"]), ("1 mois", d["m1"]), ("3 mois", d["m3"]), ("6 mois", d["m6"]),
                 ("1 an", d["y1"]), ("3 ans", d["y3"]), ("5 ans", d["y5"])], 90)
    ann = bars([("2022", d["a2022"]), ("2023", d["a2023"]), ("2024", d["a2024"]), ("2025", d["a2025"]),
                ("2026 (cours)", d["ytd"])], 35)
    vig = []
    if d["tech"] > 40: vig.append(("r", "Concentration technologique", f"La tech pèse {fr(d['tech'])} % et les 10 premières lignes {fr(d['top10'])} % ({d['tops']})."))
    vig.append(("", "Risque de change EUR/USD", "ETF non couvert : un dollar plus faible réduit la performance en euros."))
    vig.append(("", "Risque de contrepartie", "Réplication par swap (Société Générale) : surveiller l'actualité de la contrepartie."))
    if d["ytd"] > 15: vig.append(("", "Valorisation après un fort rebond", "Privilégier des versements réguliers plutôt qu'un achat unique."))
    if d["vol1"] > d["vol3"] * 1.15: vig.append(("r", "Volatilité en hausse", "La volatilité sur 1 an dépasse nettement sa moyenne sur 3 ans."))
    if d["aum"] < 300: vig.append(("r", "Encours en baisse", f"{fr(d['aum'],d=0)} M€ : surveiller le risque de fermeture."))
    if d["ter"] > 0.15: vig.append(("", "Frais en hausse", f"TER à {fr(d['ter'])} %."))
    vigh = "".join(f'<div class="alert {c}"><b>{t}.</b> {x}</div>' for c, t, x in vig)
    ech = [("0 à −3 %", "Marché proche de son sommet", "Versement habituel"),
           ("−3 à " + fr(d["dd1"], d=0) + " %", f"Correction normale (perte max. 1 an : {fr(d['dd1'])} %)", "Renforcer légèrement"),
           (fr(d["dd1"], d=0) + " à −15 %", "Zone d'opportunité", "2e tranche"),
           ("−15 à " + fr(d["dd3"], d=0) + " %", f"Correction sévère (perte max. 3 ans : {fr(d['dd3'])} %)", "Investir par tranches et tenir"),
           ("Au-delà de " + fr(d["dd3"], d=0) + " %", f"Crise (jusqu'à {fr(d['ddmax'])} % depuis 2014)", "Dernière tranche, horizon 5 ans minimum")]
    ech = "".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a, b, c in ech)
    now = datetime.now().strftime("%d/%m/%Y à %H:%M")
    src = "justETF (récupéré en direct)" if live else "valeurs de secours (mode hors ligne)"
    warn = ("" if not missing else f'<div class="alert"><b>Champs non retrouvés</b> (valeurs de secours utilisées) : {", ".join(sorted(set(missing)))}. La mise en page de justETF a peut-être changé.</div>')
    return TPL.replace("@@NOW@@", now).replace("@@SRC@@", src).replace("@@WARN@@", warn) \
        .replace("@@VERC@@", ver[0]).replace("@@VERT@@", ver[1]).replace("@@VERX@@", ver[2]) \
        .replace("@@SIG@@", sigh).replace("@@PERF@@", perf).replace("@@ANN@@", ann).replace("@@VIG@@", vigh) \
        .replace("@@ECH@@", ech).replace("@@SD1@@", fr(sd, d=1)).replace("@@SD2@@", fr(2 * sd, d=1)) \
        .replace("@@YTD@@", fr(d["ytd"], True) + " %").replace("@@Y1@@", fr(d["y1"], True) + " %") \
        .replace("@@VOL@@", fr(d["vol1"]) + " %").replace("@@DD1@@", fr(d["dd1"]) + " %") \
        .replace("@@AUM@@", fr(d["aum"], d=0) + " M€").replace("@@TER@@", fr(d["ter"]) + " %") \
        .replace("@@RR1@@", fr(d["rr1"])).replace("@@RR3@@", fr(d["rr3"])).replace("@@RR5@@", fr(d["rr5"])) \
        .replace("@@VOL3@@", fr(d["vol3"]) + " %").replace("@@VOL5@@", fr(d["vol5"]) + " %") \
        .replace("@@DD3@@", fr(d["dd3"]) + " %").replace("@@DD5@@", fr(d["dd5"]) + " %").replace("@@DDM@@", fr(d["ddmax"]) + " %") \
        .replace("@@TECH@@", fr(d["tech"]) + " %").replace("@@FIN@@", fr(d["fin"]) + " %").replace("@@SANTE@@", fr(d["sante"]) + " %") \
        .replace("@@TOP10@@", fr(d["top10"]) + " %")


TPL = """<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Suivi PSP5 – Amundi PEA S&P 500</title><style>
:root{--bg:#f6f7f9;--card:#fff;--tx:#1b2430;--mu:#667085;--bd:#e3e7ee;--ac:#1d4ed8;--up:#15803d;--dn:#b91c1c;--wa:#b45309}
@media(prefers-color-scheme:dark){:root{--bg:#0f141b;--card:#171e28;--tx:#e8ecf2;--mu:#98a2b3;--bd:#273140;--ac:#7aa2ff;--up:#4ade80;--dn:#f87171;--wa:#fbbf24}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font:15px/1.5 system-ui,sans-serif}main{max-width:1000px;margin:auto;padding:20px 16px 40px}
h1{font-size:22px;margin:4px 0}h2{font-size:16px;margin:0 0 12px}h3{font-size:14px;margin:16px 0 6px}.sub{color:var(--mu);font-size:13px}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));margin:16px 0}.g2{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(300px,1fr))}
.card{background:var(--card);border:1px solid var(--bd);border-radius:12px;padding:16px;margin-bottom:12px}.kpi .l{font-size:12px;color:var(--mu)}.kpi .v{font-size:22px;font-weight:650}
.up{color:var(--up)}.dn{color:var(--dn)}.row{display:flex;align-items:center;gap:8px;margin:7px 0;font-size:13px}.row .n{width:100px;flex:none;color:var(--mu)}
.row .b{flex:1;background:var(--bd);border-radius:4px;height:14px;overflow:hidden}.row .b i{display:block;height:100%;background:var(--ac)}.row .b i.neg{background:var(--dn)}.row .p{width:70px;text-align:right}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{padding:7px 6px;border-bottom:1px solid var(--bd);text-align:left}th{color:var(--mu)}.scroll{overflow-x:auto}
.alert{border-left:4px solid var(--wa);padding:8px 12px;margin:8px 0;background:var(--bg);border-radius:6px;font-size:13px}.alert.r{border-color:var(--dn)}.alert.g{border-color:var(--up)}
.sig{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));margin-bottom:10px}.sig div{border:1px solid var(--bd);border-radius:8px;padding:10px;font-size:13px}.sig b{display:block;font-size:15px}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}.dg{background:var(--up)}.do{background:var(--wa)}.dr{background:var(--dn)}.tag{font-size:11px;padding:2px 8px;border-radius:99px;border:1px solid var(--bd);color:var(--mu)}
.foot{font-size:12px;color:var(--mu);margin-top:16px}</style></head><body><main>
<span class="tag">PEA · Capitalisation · Réplication synthétique</span><h1>Amundi PEA S&P 500 UCITS ETF Acc</h1>
<div class="sub">ISIN FR0011871128 · Ticker PSP5 · Mis à jour le @@NOW@@ · Source : @@SRC@@</div>
@@WARN@@
<section class="grid">
<div class="card kpi"><div class="l">Depuis janvier</div><div class="v">@@YTD@@</div></div>
<div class="card kpi"><div class="l">1 an</div><div class="v">@@Y1@@</div></div>
<div class="card kpi"><div class="l">Volatilité 1 an</div><div class="v">@@VOL@@</div></div>
<div class="card kpi"><div class="l">Perte max. 1 an</div><div class="v dn">@@DD1@@</div></div>
<div class="card kpi"><div class="l">Encours</div><div class="v">@@AUM@@</div></div>
<div class="card kpi"><div class="l">Frais (TER)</div><div class="v">@@TER@@</div></div></section>
<section class="card"><h2>Signal du moment</h2><div class="sig">@@SIG@@</div>
<div class="alert @@VERC@@"><b>Lecture globale : @@VERT@@.</b> @@VERX@@</div>
<h3>Échelle d'entrée selon le repli depuis le plus haut</h3><div class="scroll"><table><tr><th>Repli</th><th>Lecture</th><th>Action suggérée</th></tr>@@ECH@@</table></div>
<h3>Variation hebdomadaire</h3><div class="sub">Mouvement ordinaire : ±@@SD1@@ % (1 écart-type = volatilité ÷ √52). Au-delà de ±@@SD2@@ %, le mouvement est exceptionnel : chercher la cause avant d'agir.</div></section>
<div class="g2"><section class="card"><h2>Performances par période</h2>@@PERF@@</section><section class="card"><h2>Performances annuelles</h2>@@ANN@@</section></div>
<div class="g2"><section class="card"><h2>Risque</h2><div class="scroll"><table><tr><th></th><th>1 an</th><th>3 ans</th><th>5 ans</th></tr>
<tr><td>Volatilité</td><td>@@VOL@@</td><td>@@VOL3@@</td><td>@@VOL5@@</td></tr><tr><td>Rendement / risque</td><td>@@RR1@@</td><td>@@RR3@@</td><td>@@RR5@@</td></tr>
<tr><td>Perte maximale</td><td>@@DD1@@</td><td>@@DD3@@</td><td>@@DD5@@</td></tr></table></div><div class="sub">Depuis le lancement : @@DDM@@. Volatilité &lt; 10 % calme, 10–20 % normale, &gt; 20 % tendue. Rendement/risque &gt; 1 très bon, 0,5–1 correct, &lt; 0,5 faible.</div></section>
<section class="card"><h2>Composition</h2><div class="sub">Technologie @@TECH@@ · Finance @@FIN@@ · Santé @@SANTE@@ · 10 premières lignes @@TOP10@@</div></section></div>
<section class="card"><h2>Points de vigilance</h2>@@VIG@@</section>
<p class="foot">Les performances passées ne préjugent pas des performances futures. Ce document n'est pas un conseil en investissement personnalisé. Ordres : en séance, 15h30–17h30 (Paris), à cours limité.</p></main></body></html>"""

if __name__ == "__main__":
    live = "--offline" not in sys.argv
    try:
        data, miss = parse(fetch()) if live else (dict(D), [])
    except Exception as e:
        print("Téléchargement impossible :", e, "→ valeurs de secours.")
        data, miss, live = dict(D), [], False
    TPL = TPL.replace("@@VIG@@", "@@VIG@@")
    open(OUT, "w", encoding="utf-8").write(build(data, miss, live))
    print("Écrit :", OUT, "| champs manquants :", miss or "aucun")
