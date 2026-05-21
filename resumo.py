"""
resumo.py — Resumo Matinal Diário
Busca notícias, clima e envia e-mail HTML formatado via Gmail SMTP.

Variáveis de ambiente necessárias (configurar como Secrets no GitHub):
  GMAIL_APP_PASSWORD    (Senha de App gerada em myaccount.google.com/apppasswords)
  NEWS_API_KEY          (newsapi.org — plano gratuito)
  OPENWEATHER_API_KEY   (openweathermap.org — plano gratuito)
  EMAIL_DESTINO         (ex: brunopessuti@gmail.com)
"""

import os
import json
import random
import datetime
import smtplib
import urllib.request
import urllib.parse
import urllib.error
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import ssl

# ─────────────────────────────────────────────
# CONFIGURAÇÃO
# ─────────────────────────────────────────────
NEWS_API_KEY       = os.environ["NEWS_API_KEY"]
OPENWEATHER_KEY    = os.environ["OPENWEATHER_API_KEY"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
EMAIL_DESTINO      = os.environ.get("EMAIL_DESTINO", "brunopessuti@gmail.com","nicolepres@gmail.com")

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
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        erro_body = e.read().decode()
        print(f"❌ HTTP {e.code} em {url}")
        print(f"   Resposta do servidor: {erro_body}")
        raise

# ─────────────────────────────────────────────
# 1. NOTÍCIAS
# ─────────────────────────────────────────────
def buscar_noticias():
    hoje = datetime.date.today().isoformat()
    ontem = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

    # /v2/everything funciona no plano gratuito da NewsAPI
    params = urllib.parse.urlencode({
        "q":        "Brasil OR mundo OR economia OR politica",
        "language": "pt",
        "from":     ontem,
        "to":       hoje,
        "sortBy":   "publishedAt",
        "pageSize": 5,
        "apiKey":   NEWS_API_KEY,
    })
    url = f"https://newsapi.org/v2/everything?{params}"
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
    # Animais
    ("🐙", "O polvo tem três corações e sangue azul. Dois corações bombeiam sangue às guelras; o terceiro, ao resto do corpo."),
    ("🐝", "Uma abelha visita entre 50 e 100 flores em uma única saída para coletar néctar."),
    ("🐬", "Golfinhos dormem com metade do cérebro de cada vez, mantendo um olho aberto para vigilância."),
    ("🐘", "Elefantes são os únicos mamíferos que não conseguem pular — e também os únicos que têm quatro joelhos."),
    ("🦎", "O gecko pode correr sobre a água graças a movimentos de suas patas que criam bolsas de ar."),
    ("🐆", "Leopardos conseguem carregar presas maiores que eles próprios até o alto de árvores para proteger a comida."),
    ("🦅", "A águia tem uma visão 4 a 8 vezes mais poderosa que a humana e consegue ver uma presa a 3 km de distância."),
    ("🐋", "A baleia-azul é o maior animal já registrado na Terra — seu coração pesa cerca de 180 kg e bate apenas 2 vezes por minuto."),
    ("🐜", "Uma colônia de formigas-cortadeiras pode carregar até 50 vezes o próprio peso e percorrer quilômetros carregando folhas."),
    ("🦈", "Os tubarões existem há 450 milhões de anos — antes mesmo das árvores aparecerem na Terra."),
    ("🐢", "As tartarugas marinhas voltam para a mesma praia onde nasceram para desovar, décadas depois, guiadas pelo campo magnético da Terra."),
    ("🦉", "As corujas conseguem girar a cabeça 270 graus porque têm 14 vértebras no pescoço — o dobro dos humanos."),
    ("🐧", "Pinguins são monogâmicos e alguns casais se reencontram todos os anos na mesma colônia após meses separados no mar."),
    ("🦁", "A juba do leão não é apenas estética — ela protege o pescoço durante brigas e indica saúde para as leoas."),
    # Espaço
    ("🌙", "Um dia na Lua dura cerca de 29 dias terrestres — o mesmo tempo que ela leva para orbitar a Terra."),
    ("🌍", "A cada ano, a Lua se afasta da Terra cerca de 3,8 cm — o mesmo ritmo que suas unhas crescem."),
    ("🚀", "No espaço, astronautas crescem até 5 cm porque a coluna vertebral se expande sem a pressão da gravidade."),
    ("⚡", "Um raio é cinco vezes mais quente que a superfície do Sol — chegando a 30.000 Kelvin."),
    ("☀️", "A luz que ilumina você agora saiu do núcleo do Sol há cerca de 100.000 anos — e levou só 8 minutos para chegar da superfície até você."),
    ("🌌", "Nossa galáxia, a Via Láctea, tem entre 200 e 400 bilhões de estrelas — e é apenas uma entre trilhões de galáxias no universo observável."),
    ("🪐", "Saturno é tão leve em relação ao seu tamanho que flutuaria na água, se houvesse um oceano grande o suficiente."),
    ("🌠", "As estrelas que você vê à noite são imagens do passado — algumas podem ter explodido há milhares de anos e você ainda não sabe."),
    ("🔭", "A sonda Voyager 1, lançada em 1977, ainda transmite sinais para a Terra — de uma distância de mais de 23 bilhões de km."),
    # Corpo humano
    ("🧠", "O cérebro humano gera cerca de 70.000 pensamentos por dia e usa apenas 20% da energia total do corpo."),
    ("🧬", "Você compartilha 60% do seu DNA com uma banana. Com um chimpanzé, esse número sobe para 98,7%."),
    ("❤️", "O coração humano bate cerca de 100.000 vezes por dia — ao longo de uma vida, isso equivale a mais de 2,5 bilhões de batimentos."),
    ("👁️", "O olho humano pode distinguir cerca de 10 milhões de cores diferentes e detectar uma chama de vela a 48 km de distância no escuro."),
    ("🦷", "Os ossos humanos são mais resistentes que o concreto — mas nossa mandíbula exerce uma força de até 90 kg ao morder."),
    ("🩸", "O corpo humano adulto tem cerca de 100.000 km de vasos sanguíneos — o suficiente para dar duas voltas e meia ao redor da Terra."),
    ("💤", "Durante o sono, o cérebro consolida memórias e elimina toxinas acumuladas durante o dia — como se fizesse uma 'limpeza' noturna."),
    ("👃", "O nariz humano consegue identificar mais de 1 trilhão de odores diferentes — bem mais do que os 10 milhões estimados anteriormente."),
    # Ciência e tecnologia
    ("🌊", "O oceano cobre 71% da Terra, mas 95% dele ainda não foi explorado pelo ser humano."),
    ("🌱", "Uma única árvore pode absorver até 22 kg de CO₂ por ano e produzir oxigênio suficiente para duas pessoas."),
    ("🍯", "O mel nunca estraga. Arqueólogos encontraram mel de 3.000 anos em tumbas egípcias — ainda comestível."),
    ("🎵", "Ouvir música que você ama libera dopamina no cérebro — o mesmo neurotransmissor ativado por comida e exercício."),
    ("💡", "Thomas Edison não inventou a lâmpada — ele aperfeiçoou um design existente e criou o sistema elétrico ao redor dela."),
    ("🌡️", "A temperatura mais fria já registrada na Terra foi -89,2°C na Antártica. A mais quente, 56,7°C no Vale da Morte, EUA."),
    ("🧪", "A água quente pode congelar mais rápido que a água fria em certas condições — fenômeno chamado de Efeito Mpemba, ainda não totalmente explicado pela ciência."),
    ("📱", "O smartphone no seu bolso tem mais poder de processamento do que todos os computadores usados pela NASA para levar o homem à Lua em 1969."),
    ("🌐", "A internet pesa aproximadamente 50 gramas — o peso de toda a eletricidade armazenada nos elétrons em movimento pela rede global."),
    ("🔋", "O Wi-Fi, o micro-ondas e o Bluetooth foram todos inventados por acidente durante pesquisas científicas com objetivos completamente diferentes."),
    # História e cultura
    ("🏛️", "A Cleópatra viveu mais próxima da construção da Pizza Hut do que das pirâmides do Egito — as pirâmides têm 2.500 anos a mais."),
    ("📚", "Shakespeare inventou mais de 1.700 palavras do inglês que usamos até hoje, incluindo 'bedroom', 'lonely' e 'generous'."),
    ("🗿", "As estátuas Moai da Ilha de Páscoa têm corpos enterrados abaixo do solo — a maioria das pessoas só conhece as cabeças."),
    ("🎨", "A tinta azul foi a mais cara da história por séculos — o pigmento ultramarino era feito de lápis-lazúli e valia mais que ouro."),
    ("⏰", "Antes dos fusos horários serem padronizados em 1884, cada cidade do mundo tinha seu próprio horário local, baseado na posição do sol."),
    ("🍕", "A pizza foi originalmente considerada comida de pobres na Itália — só se tornou popular no mundo quando imigrantes italianos a levaram para os EUA."),
    ("🎭", "Os atores do teatro grego antigo usavam máscaras enormes com bocas em formato de megafone para amplificar a voz em anfiteatros de até 14.000 pessoas."),
]

def curiosidade_do_dia():
    random.seed(int(datetime.date.today().strftime("%Y%m%d")))
    return random.choice(CURIOSIDADES)

# ─────────────────────────────────────────────
# 4. MENSAGEM MOTIVACIONAL
# ─────────────────────────────────────────────
CITACOES = [
    # Perseverança e esforço
    ("A grandeza não está em nunca cair, mas em se levantar toda vez que você cair.", "Nelson Mandela"),
    ("O sucesso é a soma de pequenos esforços repetidos dia após dia.", "Robert Collier"),
    ("Não importa o quão devagar você vá, contanto que não pare.", "Confúcio"),
    ("Tudo parece impossível até que seja feito.", "Nelson Mandela"),
    ("O único lugar onde o sucesso vem antes do trabalho é no dicionário.", "Vidal Sassoon"),
    ("Grandes realizações exigem grande dedicação.", "Vince Lombardi"),
    ("Cair sete vezes, levantar oito.", "Provérbio japonês"),
    ("A persistência é o caminho do êxito.", "Charles Chaplin"),
    ("Você não falha quando cai. Você falha quando decide não se levantar.", "Anônimo"),
    ("O caminho para o sucesso e o caminho para o fracasso são quase exatamente o mesmo.", "Colin R. Davis"),
    # Ação e coragem
    ("A melhor maneira de prever o futuro é criá-lo.", "Peter Drucker"),
    ("Você não precisa ser grande para começar, mas precisa começar para ser grande.", "Zig Ziglar"),
    ("A vida começa no fim da sua zona de conforto.", "Neale Donald Walsch"),
    ("Acredite que você pode, e você já está na metade do caminho.", "Theodore Roosevelt"),
    ("O coragem não é a ausência do medo, mas o julgamento de que outra coisa é mais importante.", "Ambrose Redmoon"),
    ("Não espere. Nunca haverá o momento certo.", "Napoleon Hill"),
    ("Uma jornada de mil milhas começa com um único passo.", "Lao Tsé"),
    ("Faça o que você pode, com o que você tem, onde você está.", "Theodore Roosevelt"),
    ("O único modo de fazer um excelente trabalho é amar o que você faz.", "Steve Jobs"),
    ("A ação é a chave fundamental para todo sucesso.", "Pablo Picasso"),
    # Mentalidade e crescimento
    ("Não é o mais forte que sobrevive, nem o mais inteligente, mas o que melhor se adapta às mudanças.", "Charles Darwin"),
    ("Seja a mudança que você quer ver no mundo.", "Mahatma Gandhi"),
    ("Você é mais corajoso do que acredita, mais forte do que parece e mais inteligente do que pensa.", "A. A. Milne"),
    ("O maior erro que você pode cometer na vida é ter medo de cometer erros.", "Elbert Hubbard"),
    ("Não limite seus desafios — desafie seus limites.", "Jerry Dunn"),
    ("A mente é tudo. Você se torna aquilo em que você pensa.", "Buda"),
    ("Quem tem um porquê para viver suporta quase qualquer como.", "Friedrich Nietzsche"),
    ("O sucesso não é final, o fracasso não é fatal. O que conta é a coragem de continuar.", "Winston Churchill"),
    ("Invista em si mesmo. Seu desenvolvimento pessoal é seu melhor investimento.", "Warren Buffett"),
    ("O pessimista vê dificuldade em cada oportunidade. O otimista vê oportunidade em cada dificuldade.", "Winston Churchill"),
    # Propósito e felicidade
    ("A felicidade não é algo pronto. Ela vem de suas próprias ações.", "Dalai Lama"),
    ("Cada dia é uma nova oportunidade de mudar sua vida.", "Anônimo"),
    ("Não conte os dias — faça os dias contarem.", "Muhammad Ali"),
    ("A vida é o que acontece enquanto você está ocupado fazendo outros planos.", "John Lennon"),
    ("O segredo da felicidade não é fazer o que se ama, mas amar o que se faz.", "James M. Barrie"),
    ("Viva como se fosse morrer amanhã. Aprenda como se fosse viver para sempre.", "Mahatma Gandhi"),
    ("A gratidão transforma o que temos em suficiente.", "Anônimo"),
    ("O sucesso é ir de fracasso em fracasso sem perder o entusiasmo.", "Winston Churchill"),
    ("Você tem exatamente a mesma quantidade de horas por dia que Beethoven, Michelangelo e Leonardo da Vinci.", "H. Jackson Brown Jr."),
    ("A vida não é medida pelo número de respirações que damos, mas pelos momentos que nos tiram o fôlego.", "Maya Angelou"),
    # Relacionamentos e impacto
    ("Trate bem as pessoas no caminho de cima, pois você vai encontrá-las novamente no caminho de baixo.", "Jimmy Durante"),
    ("O que fazemos pela vida ecoa na eternidade.", "Marco Aurélio"),
    ("Não importa o quanto você seja bem-sucedido — trate os outros com respeito.", "Anônimo"),
    ("Você pode ter tudo na vida se ajudar o suficiente de outras pessoas a conseguirem o que querem.", "Zig Ziglar"),
    ("Seja gentil, pois toda pessoa que você encontra está travando uma batalha difícil.", "Platão"),
    ("Deixe sua vida falar.", "Quaker"),
    ("O legado não é deixar algo para as pessoas. É deixar algo nas pessoas.", "Peter Strople"),
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
# 6. ENVIO VIA SMTP (Senha de App do Gmail)
# ─────────────────────────────────────────────
def enviar_email(assunto, html_body):
    # ← Adicione ou remova e-mails nesta lista
    destinatarios = [
        EMAIL_DESTINO,
        # "outro@email.com",
        # "mais_um@email.com",
    ]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"]    = EMAIL_DESTINO
    msg["To"]      = ", ".join(destinatarios)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
        servidor.login(EMAIL_DESTINO, GMAIL_APP_PASSWORD)
        servidor.sendmail(EMAIL_DESTINO, destinatarios, msg.as_string())
        print(f"✅ E-mail enviado para: {', '.join(destinatarios)}")

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
    html    = montar_html(noticias, clima, cur_emoji, cur_texto, frase, autor)
    assunto = f"☀️ Bom Dia, Bruno! Resumo Matinal — {data_fmt}"

    print("📤 Enviando e-mail via SMTP...")
    enviar_email(assunto, html)

if __name__ == "__main__":
    main()
