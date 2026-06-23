import streamlit as st
import pandas as pd
import requests
import time
import io
from urllib.parse import urlparse, parse_qs

# ─────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Influencer Stats Enricher",
    page_icon="📊",
    layout="centered",
)

# ─────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Card wrapper */
    .card {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.25rem;
    }

    /* Metric tiles */
    .metric-row { display: flex; gap: 12px; margin-top: 1rem; flex-wrap: wrap; }
    .metric-tile {
        flex: 1;
        min-width: 100px;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 0.9rem 1rem;
        text-align: center;
    }
    .metric-tile .label { font-size: 0.72rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }
    .metric-tile .value { font-size: 1.4rem; font-weight: 700; color: #0f172a; }

    /* Header strip */
    .header-strip {
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white;
        border-radius: 14px;
        padding: 2rem 2.5rem;
        margin-bottom: 2rem;
    }
    .header-strip h1 { margin: 0; font-size: 1.9rem; font-weight: 700; }
    .header-strip p { margin: 0.4rem 0 0; opacity: 0.85; font-size: 0.95rem; }

    /* Success / warning badges */
    .badge-ok   { color: #16a34a; font-weight: 600; }
    .badge-skip { color: #d97706; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────
st.markdown("""
<div class="header-strip">
  <h1>📊 Influencer Stats Enricher</h1>
  <p>Upload your influencer CSV → get views, likes, comments, ER% and CPV filled in automatically.</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# SIDEBAR — API KEYS
# ─────────────────────────────────────────
with st.sidebar:
    st.header("🔑 API Keys")
    st.caption("Keys are used only for this session and never stored.")

    yt_key = st.text_input("YouTube Data API v3 Key", type="password", placeholder="AIza...")
    apify_token = st.text_input("Apify Token", type="password", placeholder="apify_api_...")

    st.divider()
    st.subheader("⚙️ Column Names")
    st.caption("Match these to your CSV headers exactly.")

    URL_COL        = st.text_input("Post Link column",        value="Post Link  (Main Asset)")
    FOLLOWERS_COL  = st.text_input("Followers/Subs column",   value=" Followers/Subs ")
    AVG_VIEWS_COL  = st.text_input("Average Views column",    value="  Average Views ")
    VIEWS_COL      = st.text_input("Video Views column",      value=" Video Views ")
    LIKES_COL      = st.text_input("Likes column",            value=" Likes ")
    COMMENTS_COL   = st.text_input("Comments column",         value=" Comments ")
    ENGAGEMENT_COL = st.text_input("Engagement column",       value=" Engagement ")
    ER_COL         = st.text_input("Actual ER% column",       value="Actual ER%")
    CPV_COL        = st.text_input("Actual CPV column",       value="Actual CPV")
    COST_COL       = st.text_input("Total Cost column",       value="Total Cost (Incl commission)")

    BATCH_SIZE = st.number_input("Instagram batch size", min_value=1, max_value=50, value=20)

# ─────────────────────────────────────────
# YOUTUBE HELPERS
# ─────────────────────────────────────────
def get_video_id(url):
    try:
        parsed = urlparse(url)
        if "youtube.com/watch" in url:
            return parse_qs(parsed.query).get("v", [None])[0]
        if "youtu.be" in url:
            return parsed.path[1:]
        if "youtube.com/shorts/" in url:
            return parsed.path.split("/")[-1]
    except:
        pass
    return None


def get_youtube_stats(video_url, api_key):
    video_id = get_video_id(video_url)
    if not video_id:
        return None

    video_api = (
        f"https://www.googleapis.com/youtube/v3/videos"
        f"?id={video_id}&part=statistics,snippet&key={api_key}"
    )
    data = requests.get(video_api, timeout=10).json()
    if not data.get("items"):
        return None

    video = data["items"][0]
    stats = video["statistics"]
    channel_id = video["snippet"]["channelId"]

    channel_api = (
        f"https://www.googleapis.com/youtube/v3/channels"
        f"?id={channel_id}&part=statistics,contentDetails&key={api_key}"
    )
    channel_data = requests.get(channel_api, timeout=10).json()

    subscribers = 0
    uploads_playlist = None
    if channel_data.get("items"):
        item = channel_data["items"][0]
        subscribers = int(item["statistics"].get("subscriberCount", 0))
        uploads_playlist = item["contentDetails"]["relatedPlaylists"]["uploads"]

    return {
        "views": int(stats.get("viewCount", 0)),
        "likes": int(stats.get("likeCount", 0)),
        "comments": int(stats.get("commentCount", 0)),
        "followers": subscribers,
        "uploads_playlist": uploads_playlist,
    }


def get_avg_views(playlist_id, api_key):
    if not playlist_id:
        return 0

    playlist_api = (
        f"https://www.googleapis.com/youtube/v3/playlistItems"
        f"?part=contentDetails&playlistId={playlist_id}"
        f"&maxResults=10&key={api_key}"
    )
    data = requests.get(playlist_api, timeout=10).json()
    ids = [item["contentDetails"]["videoId"] for item in data.get("items", [])]
    if not ids:
        return 0

    videos_api = (
        f"https://www.googleapis.com/youtube/v3/videos"
        f"?part=statistics&id={','.join(ids)}&key={api_key}"
    )
    videos = requests.get(videos_api, timeout=10).json()
    total, count = 0, 0
    for v in videos.get("items", []):
        total += int(v["statistics"].get("viewCount", 0))
        count += 1
    return round(total / count) if count else 0

# ─────────────────────────────────────────
# INSTAGRAM HELPER
# ─────────────────────────────────────────
def scrape_instagram_batch(urls, token):
    from apify_client import ApifyClient
    client = ApifyClient(token)
    clean_urls = [u.split("?")[0].rstrip("/") for u in urls]

    run = client.actor("apify/instagram-scraper").call(
        run_input={"directUrls": clean_urls, "resultsLimit": len(clean_urls)}
    )
    items = list(client.dataset(run.default_dataset_id).iterate_items())

    results = {}
    for item in items:
        source = (
            item.get("inputUrl")
            or item.get("url")
            or item.get("postUrl")
            or ""
        )
        source = str(source).split("?")[0].rstrip("/")
        results[source] = {
            "views":    int(item.get("videoPlayCount") or item.get("videoViewCount") or 0),
            "likes":    int(item.get("likesCount") or 0),
            "comments": int(item.get("commentsCount") or 0),
        }
    return results

# ─────────────────────────────────────────
# MAIN — FILE UPLOAD
# ─────────────────────────────────────────
uploaded = st.file_uploader(
    "Upload your influencer CSV",
    type=["csv"],
    help="The file must contain a column with YouTube and/or Instagram post URLs.",
)

if uploaded:
    df = pd.read_csv(uploaded, dtype=str, keep_default_na=False)

    # ensure output cols exist
    for col in [FOLLOWERS_COL, AVG_VIEWS_COL, VIEWS_COL, LIKES_COL,
                COMMENTS_COL, ENGAGEMENT_COL, ER_COL, CPV_COL]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype("object")

    if URL_COL not in df.columns:
        st.error(f"Column **{URL_COL}** not found in your CSV. Adjust the column name in the sidebar.")
        st.stop()

    st.success(f"Loaded **{len(df)} rows** — {df[URL_COL].str.contains('youtube.com|youtu.be', na=False).sum()} YouTube · {df[URL_COL].str.contains('instagram.com', na=False).sum()} Instagram")

    with st.expander("Preview first 5 rows"):
        st.dataframe(df.head(), use_container_width=True)

    if st.button("🚀 Enrich CSV", type="primary", use_container_width=True):

        # ── Validation ──────────────────────────────────────────────────
        errors = []
        yt_rows = df[URL_COL].str.contains("youtube.com|youtu.be", na=False)
        ig_rows = df[URL_COL].str.contains("instagram.com", na=False)

        if yt_rows.any() and not yt_key:
            errors.append("YouTube rows detected — please enter your **YouTube API key** in the sidebar.")
        if ig_rows.any() and not apify_token:
            errors.append("Instagram rows detected — please enter your **Apify token** in the sidebar.")

        if errors:
            for e in errors:
                st.error(e)
            st.stop()

        # ── Progress setup ───────────────────────────────────────────────
        progress = st.progress(0, text="Starting…")
        log      = st.empty()
        total    = len(df)
        done     = 0
        errors_list = []

        # ════════════════════════════════════════════
        # INSTAGRAM
        # ════════════════════════════════════════════
        ig_idx = [(i, str(row[URL_COL]).strip()) for i, row in df.iterrows()
                  if "instagram.com" in str(row.get(URL_COL, ""))]

        if ig_idx:
            log.info(f"Scraping {len(ig_idx)} Instagram posts in batches of {BATCH_SIZE}…")

            for start in range(0, len(ig_idx), BATCH_SIZE):
                batch = ig_idx[start:start + BATCH_SIZE]
                urls  = [u for _, u in batch]

                log.info(f"Instagram batch {start + 1}–{start + len(batch)} / {len(ig_idx)}")

                try:
                    results = scrape_instagram_batch(urls, apify_token)

                    for idx, url in batch:
                        clean = url.split("?")[0].rstrip("/")
                        if clean not in results:
                            continue
                        r = results[clean]

                        engagement = r["likes"] + r["comments"]
                        er = round((engagement / r["views"]) * 100, 2) if r["views"] > 0 else 0

                        df.at[idx, VIEWS_COL]      = str(r["views"])
                        df.at[idx, LIKES_COL]       = str(r["likes"])
                        df.at[idx, COMMENTS_COL]    = str(r["comments"])
                        df.at[idx, ENGAGEMENT_COL]  = str(engagement)
                        df.at[idx, ER_COL]          = str(er)

                        cost = pd.to_numeric(df.at[idx, COST_COL], errors="coerce")
                        if pd.notna(cost) and r["views"] > 0:
                            df.at[idx, CPV_COL] = str(round(cost / r["views"], 4))

                        done += 1
                        progress.progress(done / total, text=f"Processed {done}/{total}")

                except Exception as e:
                    errors_list.append(f"Instagram batch {start}: {e}")

                time.sleep(2)

        # ════════════════════════════════════════════
        # YOUTUBE
        # ════════════════════════════════════════════
        yt_rows_list = [(i, str(row[URL_COL]).strip()) for i, row in df.iterrows()
                        if "youtube.com" in str(row.get(URL_COL, "")) or
                           "youtu.be"    in str(row.get(URL_COL, ""))]

        if yt_rows_list:
            log.info(f"Fetching {len(yt_rows_list)} YouTube videos…")

            for idx, url in yt_rows_list:
                log.info(f"YouTube → {url[:60]}…")
                try:
                    stats = get_youtube_stats(url, yt_key)
                    if not stats:
                        errors_list.append(f"Row {idx}: no YouTube data returned")
                        done += 1
                        progress.progress(done / total, text=f"Processed {done}/{total}")
                        continue

                    views    = stats["views"]
                    likes    = stats["likes"]
                    comments = stats["comments"]
                    eng      = likes + comments
                    er       = round((eng / views) * 100, 2) if views > 0 else 0
                    avg_v    = get_avg_views(stats["uploads_playlist"], yt_key)

                    df.at[idx, FOLLOWERS_COL]  = str(stats["followers"])
                    df.at[idx, AVG_VIEWS_COL]   = str(avg_v)
                    df.at[idx, VIEWS_COL]       = str(views)
                    df.at[idx, LIKES_COL]       = str(likes)
                    df.at[idx, COMMENTS_COL]    = str(comments)
                    df.at[idx, ENGAGEMENT_COL]  = str(eng)
                    df.at[idx, ER_COL]          = str(er)

                    cost = pd.to_numeric(df.at[idx, COST_COL], errors="coerce")
                    if pd.notna(cost) and views > 0:
                        df.at[idx, CPV_COL] = str(round(cost / views, 4))

                except Exception as e:
                    errors_list.append(f"Row {idx}: {e}")

                done += 1
                progress.progress(done / total, text=f"Processed {done}/{total}")

        # ════════════════════════════════════════════
        # DONE — show summary + download
        # ════════════════════════════════════════════
        progress.progress(1.0, text="✅ Complete!")
        log.empty()

        filled_yt = (df[VIEWS_COL] != "").sum() if VIEWS_COL in df.columns else 0

        st.markdown(f"""
        <div class="card">
          <b>Run complete</b><br>
          <span class="badge-ok">✔ {filled_yt} rows enriched</span>
          {"&nbsp;&nbsp;<span class='badge-skip'>⚠ " + str(len(errors_list)) + " errors</span>" if errors_list else ""}
        </div>
        """, unsafe_allow_html=True)

        if errors_list:
            with st.expander(f"⚠️ {len(errors_list)} errors (click to expand)"):
                for e in errors_list:
                    st.text(e)

        # ── Download ─────────────────────────────────────────────────────
        buf = io.StringIO()
        df.to_csv(buf, index=False, encoding="utf-8-sig")
        st.download_button(
            label="⬇️ Download Enriched CSV",
            data=buf.getvalue().encode("utf-8-sig"),
            file_name="influencers_enriched.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary",
        )

        with st.expander("Preview enriched data"):
            st.dataframe(df, use_container_width=True)
