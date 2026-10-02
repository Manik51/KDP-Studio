# 📚 KDP E-Book Architect Pro — Autonomous Publishing Studio

An end-to-end autonomous Kindle publishing system that discovers profitable micro-niches, writes full-length non-fiction books, designs publication-ready 300-DPI covers, and generates Amazon KDP SEO launch packages.

---

## 🌟 Key Features

1. **Phase 0: Automated KDP Niche Hunter**
   - Scans Amazon buyer search intent, calculates BSR potential, and discovers low-competition micro-niches (1,000–3,000 results range).
2. **Phase 1 to 4: Chain-of-Thought Deep Drafting Pipeline**
   - High-converting titles, structured chapter architecture, and iterative 1,000–1,500 word chapters with rate-limit protection.
3. **Built-in 300-DPI Amazon Cover Studio (Zero Canva Needed)**
   - Automatically renders Kindle-compliant covers (**1600 x 2560 pixels**, 1:1.6 ratio, 300 DPI) using Python Pillow with custom luxury themes.
4. **Front & Back Matter Included**
   - Copyright notice, legal disclaimers, introduction hook ("Read Sample" bait), reader review request letters, and lead magnet bonus links.
5. **One-Click Fast-Launch Kit**
   - 📥 `manuscript.md` (Full book)
   - 🖼️ `cover.jpg` (Directly uploadable to Amazon KDP)
   - 📋 `kdp_launch_sheet.txt` (Ready for 1-minute copy-pasting into KDP fields)

---

## 📱 How to Run from Your Mobile Phone 24/7 (No Laptop Needed)

### Why NOT Vercel?
Vercel is designed for quick serverless functions with a 10–15 second timeout. Generating comprehensive multi-chapter books takes 1 to 2.5 minutes, which will cause Vercel to crash with a `504 Gateway Timeout`.

### The 100% Free & Recommended Solution: **Streamlit Community Cloud**
1. Create a free account on **[GitHub](https://github.com/)** and create a new repository (e.g. `kdp-maker`).
2. Upload the files from this folder (`app.py`, `requirements.txt`, `README.md`) into your GitHub repository.
3. Go to **[share.streamlit.io](https://share.streamlit.io)** and log in with GitHub.
4. Click **"New App"** ➡️ Select your repository ➡️ Select `app.py` ➡️ Click **Deploy**.
5. Within 2 minutes, you will get a permanent public HTTPS URL (e.g. `https://my-kdp-studio.streamlit.app`).

**Open that link on your smartphone's browser!** You can turn off your laptop, generate books, download covers, and publish anytime from your phone.

---

## 💻 Local Quickstart

```bash
pip install -r requirements.txt
streamlit run app.py
```
