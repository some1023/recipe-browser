import streamlit as st
import requests
import urllib.parse

# --- セキュリティ対策 ---
try:
    RAKUTEN_APP_ID = st.secrets["RAKUTEN_APP_ID"]
    DISCORD_WEBHOOK_URL = st.secrets["DISCORD_WEBHOOK_URL"]
except Exception:
    st.error("設定エラー：APIキー（Secrets）が設定されていません。")
    st.stop()

# --- アプリのデザイン設定 ---
st.set_page_config(page_title="楽々レシピ検索 Pro", page_icon="🍳")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; }
    .search-box { background-color: #fff4f4; padding: 20px; border-radius: 15px; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🍳 楽々レシピ検索 Pro")
st.caption("ランキングがない場合は、公式の検索結果へスムーズにご案内します。")

# --- 共通関数の定義 ---
@st.cache_data(ttl=86400)
def get_categories():
    url = "https://app.rakuten.co.jp/services/api/Recipe/CategoryList/20170426"
    res = requests.get(url, params={"format": "json", "applicationId": RAKUTEN_APP_ID})
    return res.json().get('result', {})

def get_ranking(category_id):
    url = "https://app.rakuten.co.jp/services/api/Recipe/CategoryRanking/20170426"
    res = requests.get(url, params={
        "format": "json", 
        "categoryId": category_id, 
        "applicationId": RAKUTEN_APP_ID
    })
    return res.json().get("result", [])

def send_to_discord(recipe):
    payload = {
        "embeds": [{
            "title": recipe['recipeTitle'],
            "url": recipe['recipeUrl'],
            "image": {"url": recipe['foodImageUrl']},
            "description": "今日の献立案です！",
            "color": 15548997
        }]
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)
    st.toast(f"「{recipe['recipeTitle']}」を送信しました！")

# --- メイン機能 ---
with st.spinner('カテゴリ準備中...'):
    categories = get_categories()

# 入力エリア
keyword_input = st.text_input("具材を入力（スペースで複数指定）", placeholder="例：なす 豚肉")

if keyword_input:
    keywords = keyword_input.replace('　', ' ').split()
    matched_list = []
    
    for level in ['large', 'medium', 'small']:
        for cat in categories.get(level, []):
            cat_name = cat['categoryName']
            if all(k in cat_name for k in keywords):
                cid = cat['categoryId']
                if 'parentCategoryId' in cat:
                    cid = f"{cat['parentCategoryId']}-{cat['categoryId']}"
                matched_list.append({"name": cat_name, "id": cid})

    if not matched_list:
        st.warning(f"「{' + '.join(keywords)}」に一致するカテゴリはありません。")
        # カテゴリがなくても、キーワードで直接公式検索へ
        search_url = f"https://recipe.rakuten.co.jp/search/{urllib.parse.quote(' '.join(keywords))}/"
        st.link_button(f"🔍 楽天レシピで「{' '.join(keywords)}」を直接検索する", search_url)
    else:
        options = {item['name']: item['id'] for item in matched_list}
        selected_cat_name = st.selectbox("カテゴリを選択:", list(options.keys()))
        selected_cat_id = options[selected_cat_name]

        if st.button("レシピを表示する", type="primary"):
            recipes = get_ranking(selected_cat_id)
            
            if not recipes:
                # 【今回のポイント】ランキングがない場合の処理
                st.info(f"「{selected_cat_name}」のランキングは現在ありませんでした。")
                # 公式検索ページへのURLを作成（キーワードをURL用に変換）
                search_url = f"https://recipe.rakuten.co.jp/search/{urllib.parse.quote(selected_cat_name)}/"
                
                st.write("代わりに楽天レシピの**公式検索結果**を見てみましょう！")
                st.link_button(f"👉 「{selected_cat_name}」の全レシピを見る", search_url)
            else:
                for r in recipes:
                    with st.container(border=True):
                        st.subheader(r['recipeTitle'])
                        st.image(r['foodImageUrl'], use_container_width=True)
                        st.write(f"⏱ {r['recipeIndication']} / 💰 {r['recipeCost']}")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.link_button("詳細を見る", r['recipeUrl'])
                        with col2:
                            if st.button("Discordへ", key=f"ds_{r['recipeId']}"):
                                send_to_discord(r)

st.markdown("---")
st.caption("Supported by Rakuten Developers")