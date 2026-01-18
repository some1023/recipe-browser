import streamlit as st
import requests

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
    </style>
    """, unsafe_allow_html=True)

st.title("🍳 楽々レシピ検索")
st.caption("スペース区切りで複数の具材を組み合わせて検索できます。")

# --- 共通関数の定義 ---
@st.cache_data(ttl=86400) # カテゴリ一覧は1日キャッシュする
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
# 1. カテゴリデータの取得
with st.spinner('カテゴリ準備中...'):
    categories = get_categories()

# 2. 検索キーワード入力
keyword_input = st.text_input("具材を入力（スペースで複数指定）", placeholder="例：なす 豚肉")

if keyword_input:
    # 入力された文字をスペースで分割してリストにする（全角スペースにも対応）
    keywords = keyword_input.replace('　', ' ').split()
    
    matched_list = []
    for level in ['large', 'medium', 'small']:
        for cat in categories.get(level, []):
            cat_name = cat['categoryName']
            
            # 【ここが重要！】すべてのキーワードがカテゴリ名に含まれているかチェック
            if all(k in cat_name for k in keywords):
                cid = cat['categoryId']
                if 'parentCategoryId' in cat:
                    cid = f"{cat['parentCategoryId']}-{cat['categoryId']}"
                matched_list.append({"name": cat_name, "id": cid})

    if not matched_list:
        st.warning(f"「{' + '.join(keywords)}」を両方含むカテゴリは見つかりませんでした。")
    else:
        st.success(f"一致するカテゴリが {len(matched_list)} 件見つかりました。")
        
        options = {item['name']: item['id'] for item in matched_list}
        selected_cat_name = st.selectbox("カテゴリを選択:", list(options.keys()))
        selected_cat_id = options[selected_cat_name]

        if st.button("レシピを表示する", type="primary"):
            recipes = get_ranking(selected_cat_id)
            
            if not recipes:
                st.info("現在ランキングデータがありません。")
            else:
                for r in recipes:
                    with st.container(border=True):
                        st.subheader(r['recipeTitle'])
                        st.image(r['foodImageUrl'], use_container_width=True)
                        st.write(f"⏱ {r['recipeIndication']} / 💰 {r['recipeCost']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.link_button("レシピを見る", r['recipeUrl'])
                        with col2:
                            if st.button("Discord送信", key=f"ds_{r['recipeId']}"):
                                send_to_discord(r)

st.markdown("---")
st.caption("Supported by Rakuten Developers")