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
    .recipe-card { border: 1px solid #ddd; padding: 15px; border-radius: 10px; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🍳 楽々レシピ検索")
st.caption("楽天レシピのデータから、今人気の献立をご提案します。")

# --- 共通関数の定義 ---
def get_categories():
    """楽天から全カテゴリを取得する"""
    url = "https://app.rakuten.co.jp/services/api/Recipe/CategoryList/20170426"
    res = requests.get(url, params={"format": "json", "applicationId": RAKUTEN_APP_ID})
    return res.json().get('result', {})

def get_ranking(category_id):
    """カテゴリIDからランキングを取得する"""
    url = "https://app.rakuten.co.jp/services/api/Recipe/CategoryRanking/20170426"
    res = requests.get(url, params={
        "format": "json", 
        "categoryId": category_id, 
        "applicationId": RAKUTEN_APP_ID
    })
    return res.json().get("result", [])

def send_to_discord(recipe):
    """Discordに送信する"""
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
# 1. カテゴリデータの取得（最初に一度だけ実行）
if 'categories' not in st.session_state:
    with st.spinner('カテゴリ情報を読み込み中...'):
        st.session_state.categories = get_categories()

# 2. 検索キーワード入力
keyword = st.text_input("使いたい具材や料理名を入力", placeholder="例：なす、鶏肉、パスタ")

if keyword:
    # キーワードに一致するカテゴリを抽出
    matched_list = []
    for level in ['large', 'medium', 'small']:
        for cat in st.session_state.categories.get(level, []):
            if keyword in cat['categoryName']:
                cid = cat['categoryId']
                # 中・小カテゴリの場合は親IDが必要
                if 'parentCategoryId' in cat:
                    cid = f"{cat['parentCategoryId']}-{cat['categoryId']}"
                matched_list.append({"name": cat['categoryName'], "id": cid})

    if not matched_list:
        st.error(f"「{keyword}」に一致するカテゴリが見つかりませんでした。別の言葉で試してください。")
    else:
        st.success(f"「{keyword}」に関連するカテゴリが {len(matched_list)} 件見つかりました。")
        
        # セレクトボックスで詳細カテゴリを選ばせる
        options = {item['name']: item['id'] for item in matched_list}
        selected_cat_name = st.selectbox("詳しく選ぶ:", list(options.keys()))
        selected_cat_id = options[selected_cat_name]

        # 3. ランキング表示
        if st.button("このカテゴリのレシピを見る", type="primary"):
            recipes = get_ranking(selected_cat_id)
            
            if not recipes:
                st.info("現在、このカテゴリにランキングデータがありません。")
            else:
                for r in recipes:
                    with st.container(border=True):
                        st.subheader(r['recipeTitle'])
                        st.image(r['foodImageUrl'], use_container_width=True)
                        st.write(f"📝 {r['recipeDescription']}")
                        st.write(f"⏱ 調理時間目安: {r['recipeIndication']}")
                        st.write(f"💰 予算目安: {r['recipeCost']}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.link_button("楽天レシピで詳細を見る", r['recipeUrl'])
                        with col2:
                            # ボタンのキーをユニークにする
                            if st.button("Discordへ送る", key=f"ds_{r['recipeId']}"):
                                send_to_discord(r)

# クレジット表記
st.markdown("---")
st.caption("Supported by Rakuten Developers")