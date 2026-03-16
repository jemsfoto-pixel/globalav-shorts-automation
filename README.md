# 🎬 YouTube Shorts Automation

Sistema 100% autónomo y gratuito para producir y subir YouTube Shorts automáticamente.

## 🏗️ Arquitectura

```
GitHub Actions (cron cada 6h)
    → Python + MoviePy + FFmpeg
    → Gemini AI (guiones)
    → Pexels (imágenes)
    → YouTube Data API (subida)
```

## 🚀 Setup Rápido

### 1. Clona y configura

```bash
git clone <tu-repo>
cd YouTube_Automation
pip install -r requirements.txt
```

### 2. Configura las API Keys

Crea estos **GitHub Secrets** en tu repositorio:

| Secret | Descripción | Cómo obtenerla |
|--------|-------------|----------------|
| `GOOGLE_API_KEY` | Google Gemini AI | [aistudio.google.com](https://aistudio.google.com/) → Get API Key |
| `PEXELS_API_KEY` | Imágenes gratuitas | [pexels.com/api](https://www.pexels.com/api/) → Your API Key |
| `YOUTUBE_CLIENT_SECRET` | YouTube upload | [console.cloud.google.com](https://console.cloud.google.com/) → APIs → YouTube Data API v3 → OAuth |
| `YOUTUBE_TOKEN_JSON` | Auth token | Se genera en el primer login OAuth |

### 3. YouTube OAuth (primera vez)

```bash
# Ejecuta localmente para obtener el token
python scripts/uploader.py
# Copia el contenido de credentials/youtube_token.json
# Pégalo como GitHub Secret: YOUTUBE_TOKEN_JSON
```

### 4. ¡Lanza!

El workflow se ejecuta automáticamente cada 6 horas, o puedes lanzarlo manualmente:

```
GitHub → Actions → "Produce YouTube Short" → Run workflow
```

## 📂 Estructura

```
scripts/
├── main.py           # 🎯 Orquestador principal
├── research.py       # 📊 Investigación de tendencias
├── scriptwriter.py   # ✍️ Gemini AI → guiones
├── assets.py         # 🖼️ Descarga de Pexels
├── video_builder.py  # 🎬 MoviePy → vídeo
├── seo.py            # 🔍 Títulos + tags + descripción
└── uploader.py       # 📤 YouTube Data API v3
```

## ⚙️ Configuración

Edita `config.yml` para cambiar:
- **Nicho activo** (`niche.primary`)
- **Estilo visual** (colores, fuentes)
- **Duración del vídeo** (por defecto: 50s)
- **Frecuencia** (cron en el workflow)

## 📊 Nichos Disponibles

1. 🤖 **IA en 60 Segundos** — Tu canal principal (configurado por defecto)
2. 💡 **Curiosidades que no Sabías** — Datos asombrosos
3. 💰 **Finanzas para Principiantes** — Tips de inversión y ahorro

## 🔄 Ejecución Local

```bash
# Sin subir a YouTube
python scripts/main.py

# Con subida a YouTube
YOUTUBE_UPLOAD_ENABLED=true python scripts/main.py
```

## 💰 Coste Total: 0€

| Servicio | Tier Gratuito |
|----------|---------------|
| GitHub Actions | 2000 min/mes |
| Gemini AI | 15 req/min |
| Pexels | 200 req/hora |
| YouTube API | 10000 units/día (~6 uploads) |

## 📜 Licencia

Uso personal. Todos los componentes son open source.
