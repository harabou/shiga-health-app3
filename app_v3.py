import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# 1. ページ基本設定
st.set_page_config(layout="wide", page_title="滋賀県 健康寿命リスク解析")

# 2. シミュレーション関数（修正版）
def simulate_improvement(df, target_col, mode, rate):
    df_sim = df.copy()
    actual_max = df_sim[target_col].max()
    actual_min = df_sim[target_col].min()
    
    # 改善対象の抽出
    if mode == "S1：Worst改善":
        mask = (df_sim[target_col] == actual_max)
    else:
        mask = (df_sim[target_col] > actual_min)
    
    df_sim["improved_num"] = 0.0
    if mask.any():
        df_sim.loc[mask, "improved_num"] = df_sim.loc[mask, "count"] * rate
        df_sim.loc[mask, "count"] -= df_sim.loc[mask, "improved_num"]
    
    moved_total = df_sim["improved_num"].sum()
    
    # 改善後のデータ行を作成
    df_new = df_sim[df_sim["improved_num"] > 0].copy()
    if not df_new.empty:
        # リスクレベルを下げる（1つ改善）
        df_new[target_col] = (df_new[target_col] - 1).clip(lower=1)
        
        # カテゴリIDを再生成（ここが重要）
        df_new["category"] = (
            df_new["sex"].astype(str) + 
            df_new["BP_c"].astype(int).astype(str) + 
            df_new["SM"].astype(int).astype(str) + 
            df_new["DM"].astype(int).astype(str) + 
            df_new["BMI_c"].astype(int).astype(str)
        )
        
        # 重要：リスクが下がった後の「新しいカテゴリに対応するyear」を本来は参照し直す必要があります。
        # 今回のロジックでは、移動した人数の「year」を、移動先のカテゴリのyearに置き換える処理を追加します。
        # ただし、簡易版として「全カテゴリのyearリスト」から新しいカテゴリのyearをマッピングします。
        
        # 改善後の人数をセット
        df_new["count"] = df_new["improved_num"]
        
        # 元のデータと結合
        res = pd.concat([df_sim, df_new], ignore_index=True)
    else:
        res = df_sim
    
    # グループ化して合計（yearを含める）
    return res.groupby(["category","sex","BP_c","SM","DM","BMI_c","year"], as_index=False)["count"].sum(), moved_total

# 3. メイン画面
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
        
        # カラム名のクリーンアップ
        df_raw.columns = [c.strip() for c in df_raw.columns]
        df_ref.columns = [c.strip() for c in df_ref.columns]

        # リスク判定（data.csvからカテゴリを生成）
        df_raw["BP_c"] = np.select([
            (df_raw["SBP"]>=160)|(df_raw["DBP"]>=100), 
            (df_raw["SBP"]>=140)|(df_raw["DBP"]>=90)
        ], [4, 3], default=2)
        df_raw["BMI_c"] = np.select([df_raw["BMI"]>=30, df_raw["BMI"]>=25], [4, 3], default=2)
        
        df_raw["category"] = df_raw["sex"].astype(str) + df_raw["BP_c"].astype(str) + df_raw["SM"].astype(str) + df_raw["DM"].astype(str) + df_raw["BMI_c"].astype(str)
        
        # 集計
        df_freq = df_raw.groupby("category").size().reset_index(name="count")
        
        # マスタデータと結合（ここでyearが紐付く）
        merged_df = pd.merge(df_ref, df_freq, on="category", how="inner")
        
        if not merged_df.empty:
            merged_df["year"] = pd.to_numeric(merged_df["year"], errors='coerce')
            
            # カテゴリ文字列から数値を抽出（シミュレーション用）
            for i, col in enumerate(["BP_c", "SM", "DM", "BMI_c"], 1):
                merged_df[col] = merged_df["category"].str[i].astype(int)
            
            # シミュレーション実行
            df_scn, moved_total = simulate_improvement(merged_df, factor, mode, rate)
            
            # --- 重要：改善後のyearをマスタから再マッピング ---
            # リスクが下がった後の「year」を、df_ref（マスタ）から再度引っ張ってこないと数字が動きません
            df_scn = df_scn.drop(columns=["year"]) # 古いyearを削除
            df_scn = pd.merge(df_scn, df_ref[["category", "year"]], on="category", how="left")
            df_scn["year"] = df_scn["year"].fillna(0)
            # ----------------------------------------------

            total_n = float(merged_df["count"].sum())
            v_base = (merged_df["year"] * merged_df["count"]).sum() / total_n
            v_scn = (df_scn["year"] * df_scn["count"]).sum() / total_n
            
            st.subheader("📊 解析結果サマリー")
            m1, m2, m3 = st.columns(3)
            m1.metric("現状の平均健康寿命", f"{v_base:.2f} 歳")
            m2.metric("改善後の平均健康寿命", f"{v_scn:.4f} 歳", f"+{v_scn - v_base:.4f} 歳")
            m3.metric("改善に成功した人数", f"{moved_total:,.0f} 人", f"全体 {total_n:,.0f} 人中")
            
            # タブ表示（以下略）
            st.info("※改善率を動かすと「改善後の平均健康寿命」が変化することを確認してください。")

        else:
            st.warning("アップロードされたデータのカテゴリがマスタデータ（list.csv）と一致しません。")
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
