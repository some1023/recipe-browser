import streamlit as st
import requests

# --- セキュリティ対策：APIキーやWebhook URLを直接書かずに st.secrets から読み込む ---
# ※これらは後ほど Streamlit Cloud の設定画面（Secrets）に入力します。
try:
    RAKUTEN_APP_ID = st.secrets["RAKUTEN_APP_ID"]
    DISCORD_WEBHOOK_URL = st.secrets["DISCORD_WEBHOOK_URL"]
except Exception:
    st.error("設定エラー：APIキー（Secrets）が設定されていません。")
    st.stop()

# --- アプリのデザイン設定 ---
st.set_page_config(page_title="楽々レシピ検索", page_icon="🍳")

# スマホで見やすいようにデザインを少し調整
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

st.title("🍳 具材でレシピ検索")
st.caption("楽天レシピの公式データから、今人気の献立をご提案します。")

# --- メイン機能 ---
# 1. 具材の入力（最大20文字制限で安全性を確保）
ingredient = st.text_input("使いたい具材を入力", placeholder="例：豚肉、トマト、なす", max_chars=20)

if st.button("レシピを探す", type="primary"):
    if not ingredient:
        st.warning("具材を入力してください。")
    else:
        with st.spinner('最適なカテゴリを探しています...'):
            # 2. 楽天カテゴリリストの取得
            cat_url = "https://app.rakuten.co.jp/services/api/Recipe/CategoryList/20170426"
            try:
                res_cat = requests.get(cat_url, params={"format": "json", "applicationId": RAKUTEN_APP_ID})
                all_cats = res_cat.json().get('result', {})
                
                matched_cid = None
                # 大・中・小カテゴリを横断検索して、具材名が含まれるカテゴリを探す
                for level in ['large', 'medium', 'small']:
                    for cat in all_cats.get(level, []):
                        if ingredient in cat['categoryName']:
                            matched_cid = cat['categoryId']
                            if 'parentCategoryId' in cat:
                                matched_cid = f"{cat['parentCategoryId']}-{cat['categoryId']}"
                            break
                    if matched_cid: break

                if matched_cid:
                    # 3. 人気ランキングの取得
                    rank_url = "https://app.rakuten.co.jp/services/api/Recipe/CategoryRanking/20170426"
                    res_rank = requests.get(rank_url, params={
                        "format": "json", "categoryId": matched_cid, "applicationId": RAKUTEN_APP_ID
                    })
                    recipes = res_rank.json().get("result", [])

                    if recipes:
                        st.success(f"「{ingredient}」の人気レシピを見つけました！")
                        for r in recipes:
                            # 枠で囲って見やすく表示
                            with st.container(border=True):
                                st.subheader(r['recipeTitle'])
                                st.image(r['foodImageUrl'], use_container_width=True)
                                st.write(f"📝 {r['recipeDescription']}")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.link_button("詳細を見る", r['recipeUrl'])
                                with col2:
                                    # ボタンごとに固有のキーを割り当て
                                    if st.button("Discordへ送る", key=f"btn_{r['recipeId']}"):
                                        payload = {
                                            "embeds": [{
                                                "title": r['recipeTitle'],
                                                "url": r['recipeUrl'],
                                                "image": {"url": r['foodImageUrl']},
                                                "description": "今日の献立案です！",
                                                "color": 15548997
                                            }]
                                        }
                                        requests.post(DISCORD_WEBHOOK_URL, json=payload)
                                        st.toast("Discordに送信しました！")
                    else:
                        st.info("現在、このカテゴリにランキングデータがありません。")
                else:
                    st.error(f"「{ingredient}」に一致するカテゴリが見つかりませんでした。別の言葉で試してください。")
            except Exception as e:
                st.error("楽天APIとの通信に失敗しました。時間をおいて試してください。")

# クレジット表記（楽天APIの利用規約で必須）
st.markdown("---")
st.caption("Supported by Rakuten Developers")