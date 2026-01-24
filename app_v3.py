import streamlit as st
import pandas as pd
from io import StringIO
import plotly.graph_objects as go
import os

# ==========================================
# 0. ページ設定と外観用CSS
# ==========================================
st.set_page_config(page_title="健康寿命シミュレーター", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .custom-header {
        background-color: #000080;
        padding: 25px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
    }
    .custom-header h1 { 
        color: white !important; 
        margin: 0 !important; 
        font-size: 2.2rem !important; 
    }
    u {
        text-underline-offset: 4px;
        text-decoration-thickness: 2px;
        text-decoration-color: #000080;
    }
    @media print {
        div[data-testid="stSidebar"], button, header, footer, .stButton, div[data-testid="stExpander"] {
            display: none !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 1. パスワード認証機能
# ==========================================
def check_password():
    def password_entered():
        if st.session_state["password"] == "shiga123": 
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.title("🔒 関係者限定アクセス")
        st.text_input("パスワードを入力してください", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 関係者限定アクセス")
        st.text_input("パスワードを入力してください", type="password", on_change=password_entered, key="password")
        st.error("😕 パスワードが正しくありません。")
        return False
    return True

if not check_password():
    st.stop()

# ==========================================
# 2. データの定義（維持）
# ==========================================
LIST_TSV = """year,category,sex,BP,SM,DM,BMI
20.29,M1111,M,1,1,1,1
22.62,M1112,M,1,1,1,2
23.86,M1113,M,1,1,1,3
21.97,M1114,M,1,1,1,4
18.74,M1211,M,1,2,1,1
20.98,M1212,M,1,2,1,2
22.1,M1213,M,1,2,1,3
20.47,M1214,M,1,2,1,4
16.73,M1311,M,1,3,1,1
18.76,M1312,M,1,3,1,2
19.87,M1313,M,1,3,1,3
18.07,M1314,M,1,3,1,4
19.5,M2111,M,2,1,1,1
22.01,M2112,M,2,1,1,2
23.09,M2113,M,2,1,1,3
21.06,M2114,M,2,1,1,4
18.02,M2211,M,2,2,1,1
20.27,M2212,M,2,2,1,2
21.32,M2213,M,2,2,1,3
19.61,M2214,M,2,2,1,4
16.02,M2311,M,2,3,1,1
18.09,M2312,M,2,3,1,2
19.12,M2313,M,2,3,1,3
17.26,M2314,M,2,3,1,4
18.04,M3111,M,3,1,1,1
20.77,M3112,M,3,1,1,2
21.57,M3113,M,3,1,1,3
19.86,M3114,M,3,1,1,4
16.56,M3211,M,3,2,1,1
18.88,M3212,M,3,2,1,2
19.7,M3213,M,3,2,1,3
18.42,M3214,M,3,2,1,4
14.83,M3311,M,3,3,1,1
16.98,M3312,M,3,3,1,2
17.83,M3313,M,3,3,1,3
16.25,M3314,M,3,3,1,4
17.17,M4111,M,4,1,1,1
19.78,M4112,M,4,1,1,2
20.56,M4113,M,4,1,1,3
18.92,M4114,M,4,1,1,4
15.73,M4211,M,4,2,1,1
17.96,M4212,M,4,2,1,2
18.76,M4213,M,4,2,1,3
17.53,M4214,M,4,2,1,4
14.05,M4311,M,4,3,1,1
16.12,M4312,M,4,3,1,2
16.95,M4313,M,4,3,1,3
15.42,M4314,M,4,3,1,4
17.56,M1121,M,1,1,2,1
19.63,M1122,M,1,1,2,2
20.8,M1123,M,1,1,2,3
18.87,M1124,M,1,1,2,4
16.21,M1221,M,1,2,2,1
18.2,M1222,M,1,2,2,2
19.28,M1223,M,1,2,2,3
17.54,M1224,M,1,2,2,4
14.25,M1321,M,1,3,2,1
16.06,M1322,M,1,3,2,2
17.12,M1323,M,1,3,2,3
15.3,M1324,M,1,3,2,4
16.81,M2121,M,2,1,2,1
19.13,M2122,M,2,1,2,2
20.14,M2123,M,2,1,2,3
18.03,M2124,M,2,1,2,4
15.51,M2221,M,2,2,2,1
17.56,M2222,M,2,2,2,2
18.56,M2223,M,2,2,2,3
16.74,M2224,M,2,2,2,4
13.57,M2321,M,2,3,2,1
15.47,M2322,M,2,3,2,2
16.44,M2323,M,2,3,2,3
14.55,M2324,M,2,3,2,4
15.63,M3121,M,3,1,2,1
18.18,M3122,M,3,1,2,2
18.98,M3123,M,3,1,2,3
17.01,M3124,M,3,1,2,4
14.33,M3221,M,3,2,2,1
16.48,M3222,M,3,2,2,2
17.29,M3223,M,3,2,2,3
15.74,M3224,M,3,2,2,4
12.59,M3321,M,3,3,2,1
14.58,M3322,M,3,3,2,2
15.41,M3323,M,3,3,2,3
13.68,M3324,M,3,3,2,4
14.82,M4121,M,4,1,2,1
17.27,M4122,M,4,1,2,2
18.05,M4123,M,4,1,2,3
16.16,M4124,M,4,1,2,4
13.57,M4221,M,4,2,2,1
15.63,M4222,M,4,2,2,2
16.43,M4223,M,4,2,2,3
14.93,M4224,M,4,2,2,4
11.88,M4321,M,4,3,2,1
13.79,M4322,M,4,3,2,2
14.6,M4323,M,4,3,2,3
12.93,M4324,M,4,3,2,4
22.59,F1111,F,1,1,1,1
26.3,F1112,F,1,1,1,2
26.11,F1113,F,1,1,1,3
27.27,F1114,F,1,1,1,4
18.15,F1211,F,1,2,1,1
21.15,F1212,F,1,2,1,2
21.02,F1213,F,1,2,1,3
21.81,F1214,F,1,2,1,4
18.79,F1311,F,1,3,1,1
22.06,F1312,F,1,3,1,2
22.01,F1313,F,1,3,1,3
23.2,F1314,F,1,3,1,4
21.12,F2111,F,2,1,1,1
25.16,F2112,F,2,1,1,2
24.87,F2113,F,2,1,1,3
26.28,F2114,F,2,1,1,4
26.89,F2211,F,2,2,1,1
19.82,F2212,F,2,2,1,2
19.64,F2213,F,2,2,1,3
20.34,F2214,F,2,2,1,4
17.62,F2311,F,2,3,1,1
21.27,F2312,F,2,3,1,2
21.18,F2313,F,2,3,1,3
22.53,F2314,F,2,3,1,4
19.98,F3111,F,3,1,1,1
21.65,F3112,F,3,1,1,2
23.35,F3113,F,3,1,1,3
24.49,F3114,F,3,1,1,4
15.89,F3211,F,3,2,1,1
18.75,F3212,F,3,2,1,2
18.56,F3213,F,3,2,1,3
19.22,F3214,F,3,2,1,4
16.63,F3311,F,3,3,1,1
19.98,F3312,F,3,3,1,2
19.87,F3313,F,3,3,1,3
21.09,F3314,F,3,3,1,4
18.93,F4111,F,4,1,1,1
22.44,F4112,F,4,1,1,2
22.14,F4113,F,4,1,1,3
23.17,F4114,F,4,1,1,4
14.98,F4211,F,4,2,1,1
17.76,F4212,F,4,2,1,2
17.56,F4213,F,4,2,1,3
18.18,F4214,F,4,2,1,4
15.73,F4311,F,4,3,1,1
18.95,F4312,F,4,3,1,2
18.83,F4313,F,4,3,1,3
19.98,F4314,F,4,3,1,4
18.31,F1121,F,1,1,2,1
21.65,F1122,F,1,1,2,2
21.47,F1123,F,1,1,2,3
22.54,F1124,F,1,1,2,4
14.35,F1221,F,1,2,2,1
17.03,F1222,F,1,2,2,2
16.92,F1223,F,1,2,2,3
17.62,F1224,F,1,2,2,4
14.91,F1321,F,1,3,2,1
17.95,F1322,F,1,3,2,2
17.91,F1323,F,1,3,2,3
19.05,F1324,F,1,3,2,4
17.01,F2121,F,2,1,2,1
20.82,F2122,F,2,1,2,2
20.56,F2123,F,2,1,2,3
21.91,F2124,F,2,1,2,4
13.24,F2221,F,2,2,2,1
15.85,F2222,F,2,2,2,2
15.7,F2223,F,2,2,2,3
16.32,F2224,F,2,2,2,4
13.87,F2321,F,2,3,2,1
17.31,F2322,F,2,3,2,2
17.26,F2323,F,2,3,2,3
18.5,F2324,F,2,3,2,4
16,F3121,F,3,1,2,1
19.42,F3122,F,3,1,2,2
19.16,F3123,F,3,1,2,3
20.27,F3124,F,3,1,2,4
12.36,F3221,F,3,2,2,1
14.89,F3222,F,3,2,2,2
14.73,F3223,F,3,2,2,3
15.32,F3224,F,3,2,2,4
13,F3321,F,3,3,2,1
16.13,F3322,F,3,3,2,2
16.05,F3323,F,3,3,2,3
17.21,F3324,F,3,3,2,4
15.07,F4121,F,4,1,2,1
18.34,F4122,F,4,1,2,2
18.07,F4123,F,4,1,2,3
19.08,F4124,F,4,1,2,4
11.57,F4221,F,4,2,2,1
14.01,F4222,F,4,2,2,2
13.85,F4223,F,4,2,2,3
14.4,F4224,F,4,2,2,4
12.2,F4321,F,4,3,2,1
15.2,F4322,F,4,3,2,2
15.1,F4323,F,4,3,2,3
16.21,F4324,F,4,3,2,4
"""

@st.cache_data
def load_data():
    data = pd.read_csv(StringIO(LIST_TSV), sep=",")
    data.columns = data.columns.str.strip()
    for col in ["BP", "SM", "DM", "BMI"]:
        data[col] = data[col].astype(int)
    data["sex"] = data["sex"].astype(str)
    return data

df = load_data()

BP_MAP = {1: "正常", 2: "正常高値/高値", 3: "Ⅰ度高血圧", 4: "Ⅱ/Ⅲ度高血圧"}
SM_MAP = {1: "吸わない", 2: "過去に喫煙", 3: "現在喫煙"}
DM_MAP = {1: "なし", 2: "あり"}
BMI_MAP = {1: "やせ", 3: "標準", 2: "過体重", 4: "肥満"}

# ==========================================
# 3. メインUI
# ==========================================
st.markdown('<div class="custom-header"><h1>健康寿命シミュレーター</h1></div>', unsafe_allow_html=True)
st.write("生活習慣の改善による健康寿命の延伸効果を可視化します。<u>65歳以降で何年の延伸が期待できるかを示しています。</u>", unsafe_allow_html=True)

with st.expander("📌 判定基準（カテゴリー）の確認"):
    t1, t2 = st.tabs(["🩸 血圧", "⚖️ BMI"])
    with t1:
        st.markdown("| カテゴリー | 分類 | 血圧値 |\n| :--- | :--- | :--- |\n| 1 | 正常 | < 120/80 |\n| 2 | 正常高値 | 120-139/80-89 |\n| 3 | Ⅰ度高血圧 | 140-159/90-99 |\n| 4 | Ⅱ/Ⅲ度高血圧 | 160+/100+ |")
    with t2:
        st.markdown("| カテゴリー | 分類 | BMI数値 |\n| :--- | :--- | :--- |\n| 1 | やせ | < 18.5 |\n| 2 | 標準 | 18.5 - 24.9 |\n| 3 | 過体重 | 25.0 - 29.9 |\n| 4 | 肥満 | 30.0+ |")

st.markdown("### 1. 基本設定")
sex = st.radio("性別", ["M", "F"], format_func=lambda x: "男性" if x=="M" else "女性", horizontal=True)

st.markdown("---")
c_now, c_goal = st.columns(2)
with c_now:
    st.markdown("### 📋 現在")
    bp_b = st.selectbox("🩸 血圧", [1,2,3,4], format_func=lambda x: BP_MAP[x], key="bp_b")
    sm_b = st.selectbox("🚬 喫煙", [1,2,3], format_func=lambda x: SM_MAP[x], key="sm_b")
    dm_b = st.selectbox("🍬 糖尿病", [1,2], format_func=lambda x: DM_MAP[x], key="dm_b")
    bmi_b = st.selectbox("⚖️ BMI", [1,2,3,4], format_func=lambda x: BMI_MAP[x], key="bmi_b")
with c_goal:
    st.markdown("### ✨ 目標")
    bp_a = st.selectbox("🩸 血圧 ", [1,2,3,4], format_func=lambda x: BP_MAP[x], key="bp_a")
    sm_a = st.selectbox("🚬 喫煙 ", [1,2,3], format_func=lambda x: SM_MAP[x], key="sm_a")
    dm_a = st.selectbox("🍬 糖尿病 ", [1,2], format_func=lambda x: DM_MAP[x], key="dm_a")
    bmi_a = st.selectbox("⚖️ BMI ", [1,2,3,4], format_func=lambda x: BMI_MAP[x], key="bmi_a")

# ==========================================
# 4. 計算と結果
# ==========================================
def get_year(s, bp, sm, dm, bmi):
    res = df[(df["sex"] == s) & (df["BP"] == bp) & (df["SM"] == sm) & (df["DM"] == dm) & (df["BMI"] == bmi)]
    return float(res.iloc[0]["year"]) if not res.empty else None

st.markdown(" ")
if st.button("🚀 結果を表示する", use_container_width=True):
    y_b = get_year(sex, bp_b, sm_b, dm_b, bmi_b)
    y_a = get_year(sex, bp_a, sm_a, dm_a, bmi_a)

    if y_b and y_a:
        diff = y_a - y_b
        st.markdown("---")
        st.header("📊 シミュレーション結果")
        m1, m2 = st.columns(2)
        m1.metric("現状の予測健康寿命", f"{y_b:.2f} 歳")
        m2.metric("目標達成時の予測寿命", f"{y_a:.2f} 歳", delta=f"{diff:+.2f} 歳")

        if diff > 0:
            st.success(f"💡 改善により健康寿命が **{diff:.2f}年** 延びる可能性があります。")

        fig = go.Figure()
        fig.add_trace(go.Bar(x=['血圧','喫煙','糖尿病','BMI'], y=[bp_b, sm_b, dm_b, bmi_b], name='現在', marker_color='#AED6F1'))
        fig.add_trace(go.Bar(x=['血圧','喫煙','糖尿病','BMI'], y=[bp_a, sm_a, dm_a, bmi_a], name='目標', marker_color='#F5B041'))
        fig.update_layout(title="リスクレベル比較（低いほど低リスク）", barmode='group', yaxis=dict(range=[0,5]))
        st.plotly_chart(fig, use_container_width=True)

        # 出典とロゴを並べる（出典が上、ロゴが下）
        st.markdown("---")
        st.caption("※本データの出典は、Tsukinoki R,et al. Comprehensive assessment of the impact of blood pressure, body mass index, smoking, and diabetes on healthy life expectancy in Japan: NIPPON DATA90. J Epidemiol. 2025 Jan 11;35(8):349–54です。")
        
        # ロゴ表示（右寄せ）
        if os.path.exists("logo.png"):
            col_l, col_r = st.columns([3, 1])
            with col_r:
                st.image("logo.png", use_container_width=True)
表示されない場合の最終チェック
画像が表示されない理由のほとんどは、「プログラムを動かしているフォルダ」と「画像があるフォルダ」が一致していないことです。

logo.pngを右クリックして「プロパティ」を開き、ファイル名がlogo.pngであることを確認してください。

もしお使いの環境でファイル名が Logo.png（大文字）などであれば、コード側の "logo.png" もそれに合わせて書き換える必要があります。

こちらのコードで出典がロゴの上に配置されました。他に調整が必要な箇所はございますか？
