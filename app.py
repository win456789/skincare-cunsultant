import sqlite3
import time
import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai import types
from google.genai.errors import ServerError, APIError

# ดึงฟังก์ชันจัดการโปรไฟล์และคลังสินค้าจาก Supabase (database.py)
from database import (
    delete_user_profile, 
    get_all_usernames, 
    get_user_profile, 
    save_or_update_user,
    get_all_products_context
)

DB_NAME = "skincare_app.db"


# ==========================================
# 1. ฟังก์ชันจัดการ Chat History (SQLite)
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_message(role: str, content: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chat_history (role, content) VALUES (?, ?)", (role, content))
    conn.commit()
    conn.close()

def load_chat_history():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM chat_history ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in rows]

init_db()

# ==========================================
# 2. ตั้งค่า Streamlit & Gemini API
# ==========================================
st.set_page_config(page_title="Skincare Consultant", page_icon="✨")
st.title("✨Skincare Consultant")
st.caption("ผู้ช่วยวิเคราะห์และแนะนำสกินแคร์ส่วนตัว")

# ดึง API Key จาก Secrets อย่างปลอดภัย
API_KEY = st.secrets["GEMINI_API_KEY"]

base_system_prompt = """
คุณคือผู้เชี่ยวชาญด้านสกินแคร์ (Skincare Consultant)
หน้าที่ของคุณคือช่วยวิเคราะห์ปัญหาผิว แนะนำส่วนผสม และจัดเซตสกินแคร์อย่างเป็นมิตร

🚨 **กฎเหล็กที่สำคัญที่สุด (STRICT RULES)**:
1. **แนะนำเฉพาะสินค้าใน database เท่านั้น (STRICT DATABASE ONLY)**:
   - คุณต้องแนะนำเฉพาะสินค้าที่มีอยู่ในรายการ [รายการสินค้าสกินแคร์ในคลังของเรา] เท่านั้น!
   - **ห้าม** แนะนำสินค้า แบรนด์ หรือผลิตภัณฑ์ใด ๆ ที่ไม่มีชื่ออยู่ในรายการในคลังเด็ดขาด
   - หากสภาพผิวหรือโปรไฟล์ของผู้ใช้จำเป็นต้องใช้สินค้าหมวดที่ในคลังไม่มี ให้บอกผู้ใช้ตรงๆ เช่น *"สำหรับขั้นตอนนี้ ในคลังของเรายังไม่มีสินค้าที่รองรับ..."*
2. **หน้าที่ของผลิตภัณฑ์ต้องไม่ซ้ำกัน (No Duplicate Functions)**:
   - ห้ามแนะนำสินค้าหมวดหมู่เดียวกันซ้ำกันในเซตเดียว (เช่น ห้ามแนะนำ Moisturizer 2 ตัว) ยกเว้น Serum แนะนำได้มากกว่า 1 ตัว
3. **การแสดงผลสินค้า**:
   - แสดงรูปภาพสินค้าด้วยรูปแบบ Markdown เสมอ: `![ชื่อสินค้า](Image_URL)`
   - ระบุแบรนด์, ราคา, สารสำคัญ
   - ให้เพิ่ม URL Shopee ให้ทำเป็น Markdown Link เสมอ เช่น `[🛒 สั่งซื้อบน Shopee](URL)` **ห้ามลืมใส่เด็ดขาด โดยเอามาจาก database เท่านั้น**
4. **ความสำคัญของโปรไฟล์**:
   - เรียงลำดับความสำคัญข้อมูลจากซ้ายไปขวาเสมอ และให้เลือกสินค้าที่ตอบโจทย์ปัญหานั้นมากที่สุด ห้ามลืมตรวจทานโดยทำการตรวจทานอย่างน้อย 10 ครั้ง
   โดยให้ทวนว่าสินค้าทุกตัวตอบโจทย์กับแต่ละปัญหาไหม อย่างน้อย 10 ครั้ง
   - ต้องตรวจสอบสภาพผิว ปัญหาผิว และส่วนผสมที่แพ้จาก [ข้อมูลโปรไฟล์ผู้ใช้งานปัจจุบัน] ทุกครั้ง
   - **ห้าม** แนะนำสินค้าที่มีส่วนผสมที่ผู้ใช้ระบุว่าแพ้เด็ดขาด
5. **อาการเสี่ยงทางการแพทย์**:
   - หากผู้ใช้มีอาการรุนแรงหรือเป็นโรคผิวหนัง เช่น โรคสะเก็ดเงิน เริม ให้แนะนำให้พบแพทย์ผิวหนังเท่านั้น
6. **จำกัดงบประมาณต่อชิ้นอย่างเคร่งครัด (Strict Budget Limit)**:
   - ตรวจสอบราคาสินค้าจากคลังสินค้าเทียบกับ [งบประมาณสูงสุดต่อชิ้น] ของผู้ใช้
   - **ห้าม** แนะนำสินค้าที่มีราคาสูงกว่างบประมาณต่อชิ้นที่ผู้ใช้ระบุเด็ดขาด!
   - หากสินค้าตัวไหนราคาสูงกว่างบ ให้ตัดออกจากการนำเสนอทันที
   - หากในคลังไม่มีสินค้าตัวไหนอยู่ในงบ ให้แจ้งผู้ใช้ตรงๆ เช่น *"สำหรับขั้นตอนนี้ สินค้าในคลังของเราจะมีราคาเกินงบประมาณที่คุณตั้งไว้..."*
"""

components.html("""
    <script>
    try {
        let devId = localStorage.getItem("skincare_device_id");
        if (!devId) {
            devId = 'dev_' + Math.random().toString(36).substring(2, 7);
            localStorage.setItem("skincare_device_id", devId);
        }
        const parentUrl = new URL(window.parent.location.href);
        if (parentUrl.searchParams.get("device") !== devId) {
            parentUrl.searchParams.set("device", devId);
            window.open(parentUrl.href, "_parent");
        }
    } catch (e) {
        console.log("Device ID Auto-detect skipped by browser security");
    }
    </script>
""", height=0)

# ดึง device_id จาก URL query parameter
url_device_id = st.query_params.get("device", "")

# ==========================================
# 3. ส่วน Sidebar (จัดการ Profile & Settings)
# ==========================================
with st.sidebar:
    st.header("👤 โปรไฟล์ผู้ใช้งาน")
    
    default_dev_name = url_device_id if url_device_id else ""
    device_id = st.text_input("🔑 รหัสประจำเครื่อง (Device ID):", value=default_dev_name, help="ตั้งชื่อเครื่องให้ต่างกันเพื่อแยกโปรไฟล์ เช่น mac-win หรือ phone-fan")
    
    st.divider()

    all_users = get_all_usernames(device_id)
    options = ["➕ สร้างโปรไฟล์ใหม่"] + all_users
    
    selected_option = st.selectbox("เลือกโปรไฟล์:", options)
    
    if selected_option == "➕ สร้างโปรไฟล์ใหม่":
        user_name = st.text_input("กรอกชื่อใหม่:", placeholder="เช่น วิน, ปลื้ม")
    else:
        user_name = selected_option
        if st.button(f"🗑️ ลบโปรไฟล์ '{user_name}'", type="secondary", use_container_width=True):
            delete_user_profile(device_id, user_name)
            st.success(f"ลบโปรไฟล์ '{user_name}' เรียบร้อย!")
            time.sleep(1)
            st.rerun()

    existing_profile = get_user_profile(device_id, user_name) if user_name and user_name != "➕ สร้างโปรไฟล์ใหม่" else None
    
    if existing_profile and existing_profile["skin_type"]:
        default_type_list = [s.strip() for s in existing_profile["skin_type"].split(",") if s.strip()]
    else:
        default_type_list = []

    default_concerns = existing_profile["skin_concerns"] if existing_profile else ""
    default_allergies = existing_profile["allergies"] if existing_profile else ""
    default_budget = existing_profile.get("max_budget", 0) if existing_profile else 0

    with st.form("profile_form"):
        skin_options = ["ผิวมัน", "ผิวแห้ง", "ผิวผสม", "ผิวแพ้ง่าย"]
        selected_skin_types = st.multiselect("สภาพผิว:", options=skin_options, default=default_type_list)
        skin_concerns = st.text_input("ปัญหาผิวหลัก:", value=default_concerns)
        allergies = st.text_input("ส่วนผสมที่แพ้ / อยากเลี่ยง:", value=default_allergies)

        submitted = st.form_submit_button("💾 บันทึกโปรไฟล์")
        if submitted:
            if user_name and user_name.strip() != "" and user_name != "➕ สร้างโปรไฟล์ใหม่":
                skin_type_str = ", ".join(selected_skin_types) if selected_skin_types else "ไม่ระบุ"
                current_live_budget = st.session_state.get("live_budget", default_budget)
                save_or_update_user(device_id, user_name.strip(), skin_type_str, skin_concerns, allergies, current_live_budget)
                st.success(f"บันทึกโปรไฟล์ของ '{user_name}' เรียบร้อย!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("⚠️ กรุณากรอกชื่อในช่อง 'กรอกชื่อใหม่' ก่อนกดบันทึกครับ")
    
    # 🟢 ตัวเลื่อนงบประมาณ Real-time (อยู่นอก st.form เพื่อให้เลื่อนแล้วกรองทันที)
    st.divider()
    max_budget = st.slider(
        "งบประมาณสูงสุดต่อชิ้น (บาท):",
        min_value=0,
        max_value=5000,
        value=int(default_budget),
        step=100,
        key="live_budget"
    )

    # 🟢 ปุ่มล้างประวัติการสนทนา (อยู่ใน Sidebar)
    st.divider()
    if st.button("🧹 ล้างประวัติการคุยทั้งหมด", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ==========================================
# 4. ประกอบ System Prompt (ข้อมูลโปรไฟล์ + คลังสินค้า Supabase)
# ==========================================
current_profile = get_user_profile(device_id, user_name) if user_name and user_name != "➕ สร้างโปรไฟล์ใหม่" else None

if current_profile:
    user_context = f"""
\n[ข้อมูลโปรไฟล์ผู้ใช้งานปัจจุบัน]:
- ชื่อผู้ใช้: {user_name}
- สภาพผิว: {current_profile['skin_type']}
- ปัญหาผิวหลัก: {current_profile['skin_concerns']}
- ส่วนผสมที่แพ้/ต้องหลีกเลี่ยง: {current_profile['allergies']}
- งบประมาณสูงสุดต่อชิ้น: {max_budget} บาท
*คำแนะนำ*: ให้วิเคราะห์และเลือกผลิตภัณฑ์ที่เหมาะกับสภาพผิวและปัญหาผิวของผู้ใช้นี้โดยเฉพาะ และห้ามแนะนำสินค้าที่มีส่วนผสมที่ผู้ใช้แพ้หรือราคาเกิน {max_budget} บาทเด็ดขาด
"""
else:
    user_context = ""

# 🟢 ดึงข้อมูลสินค้าจาก Supabase โดยส่งงบจาก slider (max_budget) เข้าไปกรอง Real-time
user_budget = max_budget
products_context, product_count = get_all_products_context(max_budget=user_budget)

# แสดงแถบ Debug บอกจำนวนสินค้าใน Sidebar
st.sidebar.caption(f"🔍 Debug: งบปัจจุบัน = {user_budget} บาท | สินค้าที่ผ่านกรอง = {product_count} ชิ้น")

if product_count == 0 and user_budget > 0:
    products_context += f"\n⚠️ หมายเหตุ: ขณะนี้ไม่มีสินค้าในคลังที่ราคาไม่เกิน {user_budget} บาท"

system_prompt = f"{base_system_prompt}\n{user_context}\n{products_context}"

# ==========================================
# 5. จัดการ Chat Session & Gemini API Client
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=API_KEY)

# แสดงประวัติการคุย
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# กล่องรับข้อความ
if user_input := st.chat_input("พิมพ์ปรึกษาปัญหาผิว หรือถามเรื่องสกินแคร์ที่นี่..."):
    save_message("user", user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("ผู้ช่วยกำลังคิดคำตอบ..."):
            max_retries = 3
            success = False
            
            for attempt in range(max_retries):
                try:
                    response = st.session_state.client.models.generate_content(
                        model="gemini-3.5-flash-lite",
                        contents=user_input,
                        config=types.GenerateContentConfig(
                            system_instruction=system_prompt,
                            temperature=0.3,
                        )
                    )
                    
                    save_message("assistant", response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                    st.markdown(response.text)
                    success = True
                    break
                    
                except (ServerError, APIError) as e:
                    if attempt < max_retries - 1:
                        time.sleep(2)
                    else:
                        st.warning("Server มีปัญหาขณะนี้ โปรดลองใหม่อีกครั้ง")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
                    break