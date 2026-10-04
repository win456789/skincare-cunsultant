import sqlite3
import time
import streamlit as st
import streamlit.components.v1 as components
from google import genai
from google.genai import types
from google.genai.errors import ServerError, APIError

# 🟢 ดึงฟังก์ชันจัดการโปรไฟล์ คลังสินค้า และ Dynamic Few-Shot จาก Supabase (database.py)
from database import (
    delete_user_profile, 
    get_all_usernames, 
    get_user_profile,
    save_feedback, 
    save_or_update_user,
    get_all_products_context,
    get_few_shot_examples  # 🟢 เพิ่มฟังก์ชันดึงตัวอย่าง Few-Shot
)

DB_NAME = "skincare_app.db"


# ==========================================
# 1. ฟังก์ชันจัดการ Chat History (SQLite - แยกตาม Device & User)
# ==========================================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            user_name TEXT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # เพิ่มคอลัมน์ให้อัตโนมัติในกรณีที่มีตารางเดิมอยู่แล้ว
    try:
        cursor.execute("ALTER TABLE chat_history ADD COLUMN device_id TEXT")
        cursor.execute("ALTER TABLE chat_history ADD COLUMN user_name TEXT")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def save_message(device_id: str, user_name: str, role: str, content: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_history (device_id, user_name, role, content) VALUES (?, ?, ?, ?)",
        (device_id, user_name, role, content)
    )
    conn.commit()
    conn.close()

def load_chat_history(device_id: str, user_name: str):
    if not device_id or not user_name:
        return []
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM chat_history WHERE device_id = ? AND user_name = ? ORDER BY id ASC",
        (device_id, user_name)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row[0], "content": row[1]} for row in rows]

def clear_chat_history(device_id: str, user_name: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM chat_history WHERE device_id = ? AND user_name = ?",
        (device_id, user_name)
    )
    conn.commit()
    conn.close()

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
คุณคือผู้เชี่ยวชาญด้านสกินแคร์ (Skincare Consultant) หน้าที่ของคุณคือวิเคราะห์ปัญหาผิวและแนะนำสกินแคร์อย่างเป็นมิตร

🚨 [STRICT RULES - กฎเหล็ก]:
1. DATABASE ONLY: แนะนำเฉพาะสินค้าที่มีอยู่ใน [รายการสินค้าสกินแคร์ในคลังของเรา] เท่านั้น ห้ามแนะนำสินค้านอกคลังเด็ดขาด หากไม่มีหมวดที่ต้องการหรือเกินงบ ให้แจ้งผู้ใช้ตรงๆ
2. PROFILE & BUDGET CONSTRAINTS: ตรวจสอบสภาพผิว ปัญหาผิว และสารแพ้จาก [ข้อมูลโปรไฟล์ผู้ใช้งานปัจจุบัน] ห้ามแนะนำสินค้าที่มีสารแพ้ หรือราคาสูงกว่า [งบประมาณสูงสุดต่อชิ้น] เด็ดขาด
3. NO DUPLICATE ROLES: ห้ามแนะนำสินค้าหมวดเดียวกันซ้ำกันในเซต (**ยกเว้น Serum มีได้มากกว่า 1 ตัว**)
4. PRODUCT ROTATION: หากมีสินค้าที่ตรงเงื่อนไขหลายตัว ให้กระจายการแนะนำแบรนด์สลับกันอย่างหลากหลาย ห้ามยึดติดกับตัวเลือกเดิมซ้ำๆ
5. OUTDOOR/BEACH: กรณีทำกิจกรรมกลางแจ้ง/ไปทะเล ต้องเลือกเฉพาะกันแดดที่มีระบุว่า "กันน้ำ" หรือ "แดดแรง" เท่านั้น
6. MEDICAL DISCLAIMER: หากพบอาการโรคผิวหนังรุนแรง ให้แนะนำพบแพทย์ผิวหนังเท่านั้น

📋 [OUTPUT FORMAT & ROUTINE]:
- จัดเซตแบ่งเป็น "เช้า" และ "ก่อนนอน" เสมอ โดยเรียงลำดับดังนี้:
  1. Cleanser -> 2. Toner -> 3. Serum -> 4. Moisturizer -> 5. Sunscreen
- แสดงผลสินค้าทุกชิ้นด้วยรูปแบบ Markdown ดังนี้เสมอ:
  ![ชื่อสินค้า](Image_URL)
  **ชื่อสินค้า** (แบรนด์) | ราคา: XX บาท | สารสำคัญ: XX
  [🛒 สั่งซื้อบน Shopee](URL) (ดึงลิงก์จาก Database เท่านั้น)
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
            clear_chat_history(device_id, user_name)
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
    
    # ตัวเลื่อนงบประมาณ Real-time
    st.divider()
    max_budget = st.slider(
        "งบประมาณสูงสุดต่อชิ้น (บาท):",
        min_value=0,
        max_value=5000,
        value=int(default_budget),
        step=100,
        key="live_budget"
    )

    # ปุ่มล้างประวัติการสนทนาเฉพาะโปรไฟล์นี้
    st.divider()
    if st.button("🧹 ล้างประวัติการคุยของโปรไฟล์นี้", use_container_width=True):
        clear_chat_history(device_id, user_name)
        st.session_state.messages = []
        st.rerun()
    # เพิ่มใน st.sidebar ของ app.py
with st.sidebar.expander("🛠️ Debug: Prompt + Few-Shot ล่าสุด"):
    few_shot_check = get_few_shot_examples(limit=3)
    if few_shot_check:
        st.code(few_shot_check, language="markdown")
    else:
        st.warning("⚠️ ยังไม่มีเคส 👍 ใน Supabase หรือยังดึงข้อมูลไม่ได้")

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

# ดึงข้อมูลสินค้าจาก Supabase
user_budget = max_budget
products_context, product_count = get_all_products_context(max_budget=user_budget)

st.sidebar.caption(f"🔍 Debug: งบปัจจุบัน = {user_budget} บาท | สินค้าที่ผ่านกรอง = {product_count} ชิ้น")

if product_count == 0 and user_budget > 0:
    products_context += f"\n⚠️ หมายเหตุ: ขณะนี้ไม่มีสินค้าในคลังที่ราคาไม่เกิน {user_budget} บาท"

system_prompt = f"{base_system_prompt}\n{user_context}\n{products_context}"

# ==========================================
# 5. จัดการ Chat Session & Gemini API Client
# ==========================================
# 🟢 สลับประวัติแชตอัตโนมัติตาม Device ID + User Name ปัจจุบัน
profile_key = f"{device_id}_{user_name}"
if st.session_state.get("current_profile_key") != profile_key:
    st.session_state.current_profile_key = profile_key
    st.session_state.messages = load_chat_history(device_id, user_name)

if "client" not in st.session_state:
    st.session_state.client = genai.Client(api_key=API_KEY)

# 5.1 แสดงประวัติการคุยเฉพาะโปรไฟล์ปัจจุบัน
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        if message["role"] == "assistant":
            fb_key = f"fb_{idx}"
            fb = st.feedback("thumbs", key=fb_key)
            
            if fb is not None and not message.get("feedback_saved"):
                user_prompt = st.session_state.messages[idx-1]["content"] if idx > 0 else ""
                
                if fb == 1:
                    save_feedback(user_prompt, message["content"], 1, user_name)
                    message["feedback_saved"] = True
                    st.toast("ขอบคุณสำหรับ Feedback ครับ!")
                elif fb == 0:
                    with st.expander("⚠️ ช่วยบอกเหตุผลที่คำตอบนี้ยังไม่ถูกใจ เพื่อนำไปสอน AI ต่อครับ:"):
                        reason_text = st.text_input("เช่น ราคาสินค้าเกินงบ, แนะนำสินค้าซ้ำ, มีสารที่แพ้", key=f"reason_input_{idx}")
                        if st.button("ส่งข้อเสนอแนะ", key=f"btn_reason_{idx}"):
                            save_feedback(user_prompt, message["content"], -1, user_name, reason_text)
                            message["feedback_saved"] = True
                            st.success("บันทึกข้อผิดพลาดเรียบร้อย ขอบคุณครับ!")
                            st.rerun()

# 5.2 กล่องรับข้อความใหม่ และประมวลผล Gemini API
few_shot_context = get_few_shot_examples(limit=1)
if user_input := st.chat_input("พิมพ์ปรึกษาปัญหาผิว หรือถามเรื่องสกินแคร์ที่นี่..."):
    # 1. บันทึกข้อความผู้ใช้ลง SQLite และ session_state
    save_message(device_id, user_name, "user", user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 2. วาดข้อความของผู้ใช้ค้างไว้บนหน้าจอทันที
    with st.chat_message("user"):
        st.markdown(user_input)

    # 3. วาดช่องข้อความ AI พร้อมสถานะกำลังคิด
    with st.chat_message("assistant"):
        with st.spinner("ผู้ช่วยกำลังคิดคำตอบ..."):
            # 🟢 ดึงตัวอย่าง Few-Shot ล่าสุด 3 ข้อความจาก Supabase
            few_shot_context = get_few_shot_examples(limit=3)
            dynamic_system_prompt = f"{system_prompt}\n{few_shot_context}"

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = st.session_state.client.models.generate_content(
                        model="gemini-3.5-flash-lite",
                        contents=user_input,
                        config=types.GenerateContentConfig(
                            system_instruction=dynamic_system_prompt, # 🟢 ใช้ Prompt ที่รวม Few-Shot เรียบร้อยแล้ว
                            temperature=0.8,
                        )
                    )
                    
                    save_message(device_id, user_name, "assistant", response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                    break
                    
                except (ServerError, APIError) as e:
                    if attempt < max_retries - 1:
                        time.sleep(2)
                    else:
                        st.error("Server มีปัญหาขณะนี้ โปรดลองใหม่อีกครั้ง")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")
                    break

    # 4. รีเฟรชหน้าเว็บ เพื่อให้ระบบโหลดประวัติและแสดงปุ่ม Feedback ครบถ้วน
    st.rerun()