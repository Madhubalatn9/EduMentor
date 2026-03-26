import os, re

css_path = r"c:\Users\acer\OneDrive\Desktop\gi\EduMentor\edumentor\static\css\style.css"
with open(css_path, "r", encoding="utf-8") as f:
    css = f.read()

# Replace root variables
root_replacement = """:root {
  --bg: #101216;
  --bg2: #161a22;
  --surface: rgba(255, 255, 255, 0.05);
  --surface-hover: rgba(255, 255, 255, 0.08);
  --border: rgba(255, 255, 255, 0.12);
  --primary: #f59e0b;
  --primary2: #d97706;
  --cyan: #38bdf8;
  --green: #34d399;
  --amber: #fbbf24;
  --red: #f87171;
  --pink: #f472b6;
  --text: #f8fafc;
  --text2: #cbd5e1;
  --text3: #64748b;
  --sidebar-w: 240px;
  --topbar-h: 64px;
  --radius: 14px;
  --radius-sm: 8px;
  --shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
  --glow: 0 0 24px rgba(245, 158, 11, 0.25);
}"""

css = re.sub(r':root\s*\{[^}]*\}', root_replacement, css)

# Make Sidebar Dark but keep orange accents
css = css.replace("background: linear-gradient(180deg, #f59e0b, #d97706, #b45309);", "background: #161a22;")
css = css.replace("border-right: 1px solid rgba(180, 83, 9, 0.3);", "border-right: 1px solid var(--border);")
css = css.replace("rgba(255,255,255,0.25)", "var(--border)")

# Fix hardcoded bright colors
css = css.replace("background: #ffffff;", "background: var(--bg2);")
css = css.replace("background: #fff;", "background: var(--bg2);")
css = css.replace("background: #FFFFF0;", "background: var(--bg);")
css = css.replace("background: rgba(255, 255, 240, 0.92);", "background: rgba(16, 18, 22, 0.92);")
css = css.replace("background: rgba(255, 255, 255, 0.92);", "background: rgba(22, 26, 34, 0.92);")

# Remove some gradient backgrounds in favor of solid dark for containers
css = css.replace("background: linear-gradient(135deg, #fffbeb, #ffffff);", "background: var(--bg2);")
css = css.replace("background: #f8fafc;", "background: var(--bg2);")
css = css.replace("background: #f1f5f9;", "background: var(--surface);")
css = css.replace("background: rgba(0, 0, 0, 0.03);", "background: var(--surface);")
css = css.replace("background: rgba(0, 0, 0, 0.05);", "background: var(--surface);")

# Tweak code editor background to be darker/cooler to match
css = css.replace("background: #1e1e2e;", "background: #0B0E14;")

# Fix specific borders/shadows that looked bad on light mode
css = css.replace("rgba(0,0,0,0.04)", "rgba(0,0,0,0.5)")
css = css.replace("rgba(0,0,0,0.08)", "rgba(0,0,0,0.6)")

with open(css_path, "w", encoding="utf-8") as f:
    f.write(css)

print("Dark theme applied!")
