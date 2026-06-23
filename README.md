# Influencer Stats Enricher

A Streamlit app that takes your influencer CSV and automatically fills in:
- **Video Views, Likes, Comments, Engagement**
- **Engagement Rate % (ER)**
- **Cost Per View (CPV)**
- **Subscribers / Followers**
- **Average Views** (YouTube only — last 10 uploads)

Supports **YouTube** (via YouTube Data API v3) and **Instagram** (via Apify).

---

## 🚀 Deploy to Streamlit Cloud (free)

1. Push this folder to a **GitHub repo** (public or private).
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**.
3. Connect your repo, set **Main file path** to `app.py`.
4. Click **Deploy** — done!

> API keys are entered by the user in the sidebar at runtime. They are never stored.

---

## 🔑 Getting API Keys

### YouTube Data API v3
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → **APIs & Services** → **Enable APIs**
3. Search and enable **YouTube Data API v3**
4. Go to **Credentials** → **Create Credentials** → **API key**

### Apify Token (Instagram)
1. Sign up at [apify.com](https://apify.com)
2. Go to **Settings** → **Integrations** → copy your **API token**
3. Make sure you have access to the `apify/instagram-scraper` actor

---

## 🖥 Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 📋 CSV Format

Your CSV must have a column containing post URLs (default: `Post Link  (Main Asset)`).  
All other column names are configurable in the sidebar.

| Column | Default name |
|---|---|
| Post URL | `Post Link  (Main Asset)` |
| Followers | ` Followers/Subs ` |
| Average Views | `  Average Views ` |
| Video Views | ` Video Views ` |
| Likes | ` Likes ` |
| Comments | ` Comments ` |
| Engagement | ` Engagement ` |
| ER% | `Actual ER%` |
| CPV | `Actual CPV` |
| Total Cost | `Total Cost (Incl commission)` |
