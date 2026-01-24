import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import os

# ==========================================
# 1. ページ基本設定
# ==========================================
st.set_page_config(layout="wide", page_title="滋賀県 健康寿命リスク解析")

# ==========================================
# 2. パスワード認証機能
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
    else:
        return True

if not check_password():
    st.stop()

# ==========================================
# 3. シミュレーション関数 (ロジック維持)
# ==========================================
def simulate_improvement(df, target_col, mode, rate):
    df_sim = df.copy()
    actual_max = df_sim[target_col].max()
    actual_min = df_sim[target_col].min()
    
    if mode == "S1：Worst改善":
        mask = (df_sim[target_col] == actual_max)
    else:
        mask = (df_sim[target_col] > actual_min)
    
    df_sim["improved_num"] = 0.0
    if mask.any():
        df_sim.loc[mask, "improved_num"] = df_sim.loc[mask, "count"] * rate
        df_sim.loc[mask, "count"] -= df_sim.loc[mask, "improved_num"]
    
    moved_total = df_sim["improved_num"].sum()
    
    df_new = df_sim[df_sim["improved_num"] > 0].copy()
    if not df_new.empty:
        df_new[target_col] = (df_new[target_col] - 1).clip(lower=1)
        df_new["category"] = (
            df_new["sex"].astype(str) + 
            df_new["BP_c"].astype(int).astype(str) + 
            df_new["SM"].astype(int).astype(str) + 
            df_new["DM"].astype(int).astype(str) + 
            df_new["BMI_c"].astype(int).astype(str)
        )
        df_new["count"] = df_new["improved_num"]
        res = pd.concat([df_sim, df_new], ignore_index=True)
    else:
        res = df_sim
    
    return res.groupby(["category","sex","BP_c","SM","DM","BMI_c"], as_index=False)["count"].sum(), moved_total

# ==========================================
# 4. メインUI
# ==========================================
st.markdown("<h1 style='color: #007BBB; border-bottom: 3px solid #007BBB;'>💧 滋賀県 健康寿命リスク解析ツール</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.header("📂 データ読み込み")
    data_file = st.file_uploader("1. data.csv", type="csv")
    list_file = st.file_uploader("2. list.csv", type="csv")
    st.divider()
    st.header("⚙️ 設定")
    f_map = {"BP_c":"血圧", "SM":"喫煙", "DM":"血糖", "BMI_c":"肥満"}
    f_label = st.selectbox("項目", list(f_map.values()))
    factor = [k for k, v in f_map.items() if v == f_label][0]
    mode = st.selectbox("対象", ["S1：Worst改善", "S2：Except Best改善"])
    rate = st.slider("改善率", 0.0, 1.0, 0.20, step=0.01)

if data_file and list_file:
    try:
        df_raw = pd.read_csv(data_file)
        df_ref = pd.read_csv(list_file)
        
        df_raw.columns = [c.strip() for c in df_raw.columns]
        df_ref.columns = [c.strip() for c in df_ref.columns]

        df_raw["BP_c"] = np.select([(df_raw["SBP"]>=160)|(df_raw["DBP"]>=100), (df_raw["SBP"]>=140)|(df_raw["DBP"]>=90)], [4, 3], default=2)
        df_raw["BMI_c"] = np.select([df_raw["BMI"]>=30, df_raw["BMI"]>=25], [4, 3], default=2)
        df_raw["category"] = df_raw["sex"].astype(str) + df_raw["BP_c"].astype(str) + df_raw["SM"].astype(str) + df_raw["DM"].astype(str) + df_raw["BMI_c"].astype(str)
        
        df_freq = df_raw.groupby("category").size().reset_index(name="count")
        merged_df = pd.merge(df_ref, df_freq, on="category", how="inner")
        
        if not merged_df.empty:
            merged_df["year"] = pd.to_numeric(merged_df["year"], errors='coerce')
            for i, col in enumerate(["BP_c", "SM", "DM", "BMI_c"], 1):
                merged_df[col] = merged_df["category"].str[i].astype(int)
            
            df_scn, moved_total = simulate_improvement(merged_df, factor, mode, rate)
            df_scn = pd.merge(df_scn, df_ref[["category", "year"]], on="category", how="left")
            df_scn["year"] = pd.to_numeric(df_scn["year"], errors='coerce').fillna(0)

            total_n = float(merged_df["count"].sum())
            v_base = (merged_df["year"] * merged_df["count"]).sum() / total_n
            v_scn = (df_scn["year"] * df_scn["count"]).sum() / total_n
            
            st.subheader("📊 解析結果サマリー")
            m1, m2, m3 = st.columns(3)
            m1.metric("現状の平均健康寿命", f"{v_base:.2f} 歳")
            m2.metric("改善後の平均健康寿命", f"{v_scn:.4f} 歳", f"+{v_scn - v_base:.4f} 歳")
            m3.metric("改善に成功した人数", f"{moved_total:,.0f} 人", f"全体 {total_n:,.0f} 人中")

            t1, t2, t3 = st.tabs(["📉 分布比較", "🔄 リスクカテゴリ別増減", "🗺️ リスク構造"])
            
            with t1:
                db = merged_df.groupby("year")["count"].sum().reset_index().sort_values("year")
                ds = df_scn.groupby("year")["count"].sum().reset_index().sort_values("year")
                fig = go.Figure()
                fig.add_trace(go.Bar(x=db["year"], y=db["count"], name="現状", marker_color="gray", opacity=0.4))
                fig.add_trace(go.Bar(x=ds["year"], y=ds["count"], name="改善後", marker_color="#007BBB", opacity=0.7))
                fig.update_layout(barmode='overlay', title="健康寿命ごとの人数分布", xaxis_title="健康寿命 (歳)", yaxis_title="人数")
                st.plotly_chart(fig, use_container_width=True)
            
            with t2:
                df_diff = pd.merge(
                    merged_df[["category", "count"]].rename(columns={"count":"base"}), 
                    df_scn[["category", "count"]].rename(columns={"count":"scn"}), 
                    on="category", how="outer"
                ).fillna(0)
                df_diff["diff"] = df_diff["scn"] - df_diff["base"]
                plot_diff = df_diff[df_diff["diff"] != 0].sort_values("diff")
                
                if not plot_diff.empty:
                    plot_diff["category"] = plot_diff["category"].astype(str)
                    fig_bar = px.bar(plot_diff, x="category", y="diff", color="diff", color_continuous_scale="RdBu", title="カテゴリ別の人数増減")
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.info("改善率を動かすと、ここにカテゴリ別の移動が表示されます。")

            with t3:
                c1, c2 = st.columns(2)
                c1.plotly_chart(px.treemap(merged_df, path=[px.Constant("現状"), "sex", "category"], values="count", color="year", color_continuous_scale="RdBu"), use_container_width=True)
                c2.plotly_chart(px.treemap(df_scn, path=[px.Constant("改善後"), "sex", "category"], values="count", color="year", color_continuous_scale="RdBu"), use_container_width=True)

            # --- 出典とロゴの表示エリア ---
            st.divider()
            col_f1, col_f2 = st.columns([0.7, 0.3])
            
            with col_f1:
                st.markdown("""
                **出典** Tsukinoki R,et al. Comprehensive assessment of the impact of blood pressure, body mass index, smoking, and diabetes on healthy life expectancy in Japan: NIPPON DATA90. J Epidemiol. 2025 Jan 11;35(8):349–54
                """)
            
            with col_f2:
                if os.path.exists("logo.png"):
                    st.image("logo.png", width=150)

        else:
            st.warning("データが一致しません。")
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")





