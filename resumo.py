"""
resumo.py — Resumo Matinal Diário
Busca notícias, clima e envia e-mail HTML formatado via Gmail API.

Variáveis de ambiente necessárias (configurar como Secrets no GitHub):
  GMAIL_CLIENT_ID
  GMAIL_CLIENT_SECRET
  GMAIL_REFRESH_TOKEN
  NEWS_API_KEY          (newsapi.org — plano gratuito)
  OPENWEATHER_API_KEY   (openweathermap.org — plano gratuito)
  EMAIL_DESTINO         (ex: brunopessuti@gmail.com)
"""

import os
import json
import random
import datetime
import urllib.request
import urllib.parse
import urllib.error
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import base64
import ssl

# ─────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────
NEWS_API_KEY        = os.environ["NEWS_API_KEY"]
OPENWEATHER_KEY     = os.environ["OPENWEATHER_API_KEY"]
GMAIL_CLIENT_ID     = os.environ["GMAIL_CLIENT_ID"]
GMAIL_CLIENT_SECRET = os.environ["GMAIL_CLIENT_SECRET"]
GMAIL_REFRESH_TOKEN = os.environ["GMAIL_REFRESH_TOKEN"]
EMAIL_DESTINO       = os.environ.get("EMAIL_DESTINO", "brunopessuti@gmail.com")

CIDADE              = "Curitiba,BR"
CIDADE_NOME         = "Curitiba"
PAIS_NOTICIAS       = "br"

# ─────────────────────────────────────────────
# HELPERS HTTP
# ─────────────────────────────────────────────
ctx = ssl.create_default_context()

def get_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
        return json.loads(r.read().decode())

def post_json(url, data, headers=None):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers or {})
    with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
        return json.loads(r.read().decode())

# ─────────────────────────────────────────────
# 1. NOTÍCIAS
# ─────────────────────────────────────────────
def buscar_noticias():
    hoje = datetime.date.today().isoformat()
    ontem = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

    # /v2/everything funciona no plano gratuito da NewsAPI
    url = (
        "https://newsapi.org/v2/everything"
        f"?q=Brasil+OR+mundo+OR+economia+OR+política"
        f"&language=pt"
        f"&from={ontem}"
        f"&to={hoje}"
        f"&sortBy=publishedAt"
        f"&pageSize=5"
        f"&apiKey={NEWS_API_KEY}"
    )
    dados = get_json(url)
    artigos = dados.get("articles", [])

    noticias = []
    for a in artigos[:5]:
        titulo = a.get("title", "") or ""
        # Remove sufixo " - Nome do Veículo" do título
        titulo = titulo.split(" - ")[0].strip()
        if not titulo or titulo == "[Removed]":
            continue
        noticias.append({
            "titulo":    titulo,
            "descricao": a.get("description") or "",
            "fonte":     a.get("source", {}).get("name", ""),
            "url":       a.get("url", ""),
        })
    return noticias[:5]

# ─────────────────────────────────────────────
# 2. CLIMA
# ─────────────────────────────────────────────
ICONES_CLIMA = {
    "Clear": "☀️", "Clouds": "☁️", "Rain": "🌧️",
    "Drizzle": "🌦️", "Thunderstorm": "⛈️", "Snow": "❄️",
    "Mist": "🌫️", "Fog": "🌫️", "Haze": "🌫️",
}

def buscar_clima():
    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?q={urllib.parse.quote(CIDADE)}"
        f"&appid={OPENWEATHER_KEY}"
        f"&units=metric&lang=pt_br"
    )
    d = get_json(url)
    main    = d["main"]
    weather = d["weather"][0]
    return {
        "icone":      ICONES_CLIMA.get(weather.get("main", ""), "🌡️"),
        "condicao":   weather.get("description", "").capitalize(),
        "temp_atual": round(main["temp"]),
        "temp_min":   round(main["temp_min"]),
        "temp_max":   round(main["temp_max"]),
        "umidade":    main["humidity"],
        "vento_kmh":  round(d.get("wind", {}).get("speed", 0) * 3.6),
    }

# ─────────────────────────────────────────────
# 3. CURIOSIDADE DO DIA
# ─────────────────────────────────────────────
CURIOSIDADES = [
    ("🐙", "O polvo tem três corações e sangue azul. Dois corações bombeiam sangue às guelras; o terceiro, ao resto do corpo."),
    ("🌙", "Um dia na Lua dura cerca de 29 dias terrestres — o mesmo tempo que ela leva para orbitar a Terra."),
    ("🧠", "O cérebro humano gera cerca de 70.000 pensamentos por dia e usa apenas 20% da energia total do corpo."),
    ("🐝", "Uma abelha visita entre 50 e 100 flores em uma única saída para coletar néctar."),
    ("🌊", "O oceano cobre 71% da Terra, mas 95% dele ainda não foi explorado pelo ser humano."),
    ("🌍", "A cada ano, a Lua se afasta da Terra cerca de 3,8 cm — o mesmo ritmo que suas unhas crescem."),
    ("🍯", "O mel nunca estraga. Arqueólogos encontraram mel de 3.000 anos em tumbas egípcias — ainda comestível."),
    ("🐘", "Elefantes são os únicos animais que não conseguem pular. Suas pernas são tão pesadas que nunca perdem contato total com o solo."),
    ("⚡", "Um raio é cinco vezes mais quente que a superfície do Sol — chegando a 30.000 Kelvin."),
    ("🌱", "Uma única árvore pode absorver até 22 kg de CO₂ por ano e produzir oxigênio suficiente para duas pessoas."),
    ("🐬", "Golfinhos dormem com metade do cérebro de cada vez, mantendo um olho aberto para vigilância."),
    ("🧬", "Você compartilha 60% do seu DNA com uma banana. Com um chimpanzé, esse número sobe para 98,7%."),
    ("🚀", "No espaço, astronautas crescem até 5 cm porque a coluna vertebral se expande sem a pressão da gravidade."),
    ("🎵", "Ouvir música que você ama libera dopamina no cérebro — o mesmo neurotransmissor ativado por comida e exercício."),
    ("🦎", "O gecko pode correr sobre a água graças a movimentos de suas patas que criam bolsas de ar."),
]

def curiosidade_do_dia():
    random.seed(int(datetime.date.today().strftime("%Y%m%d")))
    return random.choice(CURIOSIDADES)

# ─────────────────────────────────────────────
# 4. MENSAGEM MOTIVACIONAL
# ─────────────────────────────────────────────
CITACOES = [
    ("A grandeza não está em nunca cair, mas em se levantar toda vez que você cair.", "Nelson Mandela"),
    ("O único modo de fazer um excelente trabalho é amar o que você faz.", "Steve Jobs"),
    ("Não é o mais forte que sobrevive, nem o mais inteligente, mas o que melhor se adapta às mudanças.", "Charles Darwin"),
    ("Você não precisa ser grande para começar, mas precisa começar para ser grande.", "Zig Ziglar"),
    ("O sucesso é a soma de pequenos esforços repetidos dia após dia.", "Robert Collier"),
    ("Acredite que você pode, e você já está na metade do caminho.", "Theodore Roosevelt"),
    ("Não importa o quão devagar você vá, contanto que não pare.", "Confúcio"),
    ("A melhor maneira de prever o futuro é criá-lo.", "Peter Drucker"),
    ("Tudo parece impossível até que seja feito.", "Nelson Mandela"),
    ("Você é mais corajoso do que acredita, mais forte do que parece.", "A. A. Milne"),
    ("O único lugar onde o sucesso vem antes do trabalho é no dicionário.", "Vidal Sassoon"),
    ("A vida começa no fim da sua zona de conforto.", "Neale Donald Walsch"),
    ("Seja a mudança que você quer ver no mundo.", "Mahatma Gandhi"),
    ("Grandes realizações exigem grande dedicação.", "Vince Lombardi"),
    ("Cada dia é uma nova oportunidade de mudar sua vida.", "Anônimo"),
]

def mensagem_motivacional():
    random.seed(int(datetime.date.today().strftime("%Y%m%d")) + 1)
    return random.choice(CITACOES)

# ─────────────────────────────────────────────
# 5. MONTAR E-MAIL HTML
# ─────────────────────────────────────────────
CORES    = ["#1a73e8", "#e53935", "#f57c00", "#43a047", "#8e24aa"]
FUNDOS   = ["#f8fbff", "#fff8f8", "#fffbf5", "#f5fdf6", "#fdf3ff"]

def card_noticia(n, idx):
    cor   = CORES[idx % len(CORES)]
    fundo = FUNDOS[idx % len(FUNDOS)]
    fonte = f" · {n['fonte']}" if n['fonte'] else ""
    desc  = (
        f"<p style='margin:4px 0 0;font-size:13px;color:#555;line-height:1.5;'>{n['descricao']}</p>"
        if n['descricao'] else ""
    )
    return f"""
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:12px;">
    <tr><td style="padding:12px 16px;background:{fundo};border-left:4px solid {cor};border-radius:0 8px 8px 0;">
        <p style="margin:0 0 3px;font-size:11px;color:{cor};font-weight:600;text-transform:uppercase;letter-spacing:1px;">📌 Notícia{fonte}</p>
        <p style="margin:0;font-size:14px;color:#222;font-weight:600;">{n['titulo']}</p>
        {desc}
    </td></tr>
    </table>"""

def montar_html(noticias, clima, cur_emoji, cur_texto, frase, autor):
    hoje = datetime.date.today()
    dias = ["Segunda-feira","Terça-feira","Quarta-feira","Quinta-feira","Sexta-feira","Sábado","Domingo"]
    meses = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"]
    dia_semana = dias[hoje.weekday()]
    data_fmt = f"{hoje.day} de {meses[hoje.month-1]} de {hoje.year}"
    cards = "\n".join(card_noticia(n, i) for i, n in enumerate(noticias))

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:30px 0;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0" style="background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);">
<tr><td style="background:linear-gradient(135deg,#1a73e8,#0d47a1);padding:36px 40px;text-align:center;">
  <p style="margin:0;color:#c8e6ff;font-size:13px;letter-spacing:2px;text-transform:uppercase;">{dia_semana}</p>
  <h1 style="margin:8px 0 4px;color:#fff;font-size:32px;font-weight:700;">☀️ Bom Dia, Bruno!</h1>
  <p style="margin:0;color:#90caf9;font-size:15px;">{data_fmt}</p>
</td></tr>
<tr><td style="padding:28px 40px 0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#e3f2fd,#bbdefb);border-radius:12px;padding:20px 24px;">
  <tr><td>
    <p style="margin:0 0 4px;font-size:11px;color:#1565c0;letter-spacing:2px;text-transform:uppercase;font-weight:600;">🌤 Tempo em {CIDADE_NOME}</p>
    <h2 style="margin:4px 0 6px;font-size:24px;color:#0d47a1;">{clima['icone']} {clima['condicao']} · {clima['temp_atual']}°C</h2>
    <p style="margin:0;color:#1565c0;font-size:14px;">Mín <strong>{clima['temp_min']}°C</strong> · Máx <strong>{clima['temp_max']}°C</strong> &nbsp;|&nbsp; Umidade <strong>{clima['umidade']}%</strong> &nbsp;|&nbsp; Vento <strong>{clima['vento_kmh']} km/h</strong></p>
  </td></tr></table>
</td></tr>
<tr><td style="padding:20px 40px 0;"><hr style="border:none;border-top:1px solid #e8edf2;"></td></tr>
<tr><td style="padding:20px 40px 0;">
  <p style="margin:0 0 16px;font-size:11px;color:#555;letter-spacing:2px;text-transform:uppercase;font-weight:600;">📰 Principais Notícias do Dia</p>
  {cards}
</td></tr>
<tr><td style="padding:20px 40px 0;"><hr style="border:none;border-top:1px solid #e8edf2;"></td></tr>
<tr><td style="padding:20px 40px 0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#fff8e1,#fffde7);border-radius:12px;padding:20px 24px;">
  <tr><td>
    <p style="margin:0 0 8px;font-size:11px;color:#f9a825;letter-spacing:2px;text-transform:uppercase;font-weight:600;">🔍 Curiosidade do Dia</p>
    <p style="margin:0;font-size:14px;color:#333;line-height:1.7;">{cur_emoji} {cur_texto}</p>
  </td></tr></table>
</td></tr>
<tr><td style="padding:20px 40px 0;"><hr style="border:none;border-top:1px solid #e8edf2;"></td></tr>
<tr><td style="padding:20px 40px 0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:linear-gradient(135deg,#e8f5e9,#c8e6c9);border-radius:12px;padding:24px;">
  <tr><td style="text-align:center;">
    <p style="margin:0 0 10px;font-size:11px;color:#2e7d32;letter-spacing:2px;text-transform:uppercase;font-weight:600;">💚 Mensagem do Dia</p>
    <p style="margin:0;font-size:18px;color:#1b5e20;font-weight:700;line-height:1.5;font-style:italic;">"{frase}"</p>
    <p style="margin:8px 0 16px;font-size:13px;color:#388e3c;">— {autor}</p>
    <p style="margin:0;font-size:14px;color:#2e7d32;line-height:1.6;">Aproveite bem o seu dia! Cada manhã é uma nova oportunidade. 🚀</p>
  </td></tr></table>
</td></tr>
<tr><td style="padding:28px 40px 32px;text-align:center;">
  <p style="margin:0;font-size:12px;color:#aaa;">Resumo gerado automaticamente por GitHub Actions · {data_fmt}</p>
  <p style="margin:4px 0 0;font-size:11px;color:#ccc;">Criado especialmente para você, Bruno 👋</p>
</td></tr>
</table>
</td></tr>
</table>
</body></html>"""

# ─────────────────────────────────────────────
# 6. GMAIL API
# ─────────────────────────────────────────────
def obter_access_token():
    resp = post_json("https://oauth2.googleapis.com/token", {
        "client_id":     GMAIL_CLIENT_ID,
        "client_secret": GMAIL_CLIENT_SECRET,
        "refresh_token": GMAIL_REFRESH_TOKEN,
        "grant_type":    "refresh_token",
    })
    return resp["access_token"]

def enviar_email(access_token, assunto, html_body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"]    = EMAIL_DESTINO
    msg["To"]      = EMAIL_DESTINO
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    payload = json.dumps({"raw": raw}).encode()
    req = urllib.request.Request(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        data=payload,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, context=ctx, timeout=20) as r:
        return json.loads(r.read().decode())

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    hoje = datetime.date.today()
    meses = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"]
    data_fmt = f"{hoje.day} de {meses[hoje.month-1]} de {hoje.year}"

    print("📰 Buscando notícias...")
    noticias = buscar_noticias()
    print(f"   {len(noticias)} notícias encontradas.")

    print("🌤 Buscando clima em Curitiba...")
    clima = buscar_clima()
    print(f"   {clima['condicao']}, {clima['temp_atual']}°C")

    print("🔍 Gerando curiosidade do dia...")
    cur_emoji, cur_texto = curiosidade_do_dia()

    print("💚 Gerando mensagem motivacional...")
    frase, autor = mensagem_motivacional()

    print("✉️  Montando e-mail HTML...")
    html   = montar_html(noticias, clima, cur_emoji, cur_texto, frase, autor)
    assunto = f"☀️ Bom Dia, Bruno! Resumo Matinal — {data_fmt}"

    print("🔑 Obtendo token de acesso Gmail...")
    token = obter_access_token()

    print("📤 Enviando e-mail...")
    resultado = enviar_email(token, assunto, html)
    print(f"✅ E-mail enviado com sucesso! ID: {resultado.get('id', '???')}")

if __name__ == "__main__":
    main()
