import json
import time
import streamlit as st
from google import genai
from google.genai import types
from database import supabase

base_system_prompt = """
คุณคือผู้เชี่ยวชาญด้านสกินแคร์ (Skincare Consultant)
หน้าที่ของคุณคือช่วยวิเคราะห์ปัญหาผิว แนะนำส่วนผสม และจัดเซตสกินแคร์อย่างเป็นมิตร
"""

# 🟢 ดึง API Key จาก st.secrets เท่านั้น ปลอดภัย 100% ไม่หลุดขึ้น Git แน่นอน
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception as e:
    print("❌ ไม่พบ GEMINI_API_KEY ใน .streamlit/secrets.toml")
    print("💡 โปรดตรวจสอบว่ามีไฟล์ .streamlit/secrets.toml ในโฟลเดอร์โปรเจกต์แล้วหรือยัง")
    raise 

def generate_corrected_response(client, user_input, bad_ai_response, user_reason):
    """ส่งเคสที่ตอบผิดไปให้ Gemini แก้ไขคำตอบตามเหตุผลของผู้ใช้"""
    correction_prompt = f"""
คุณคือผู้เชี่ยวชาญด้านสกินแคร์

[คำถามของผู้ใช้]: {user_input}
[คำตอบเดิมที่ผิด]: {bad_ai_response}
[เหตุผลที่ผู้ใช้ระบุว่าผิด]: {user_reason}

โปรดวิเคราะห์จุดผิดพลาดตามเหตุผลของผู้ใช้ แล้วเขียน "คำตอบใหม่ที่ถูกต้อง 100%" ออกมาเพียงอย่างเดียว โดยไม่ต้องมีคำเกริ่น
"""
    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=correction_prompt,
            config=types.GenerateContentConfig(temperature=0.2)
        )
        return response.text
    except Exception as e:
        print(f"⚠️ เกิดข้อผิดพลาดขณะให้ Gemini แก้คำตอบ: {e}")
        return None

def export_feedback_to_jsonl(filename="skincare_tuning_dataset.jsonl"):
    print("🚀 เริ่มสแกนข้อมูลจาก Supabase...")
    client = genai.Client(api_key=API_KEY)
    jsonl_lines = []

    # ----------------------------------------------------
    # ส่วนที่ 1: ดึงเคส 👍 (Rating = 1)
    # ----------------------------------------------------
    good_res = supabase.table("feedback_logs").select("user_input, ai_response").eq("rating", 1).execute()
    good_data = good_res.data or []
    print(f"📦 พบเคสที่ได้รับ 👍 ทั้งหมด: {len(good_data)} เคส")

    for item in good_data:
        entry = {
            "systemInstruction": {"parts": [{"text": base_system_prompt.strip()}]},
            "contents": [
                {"role": "user", "parts": [{"text": item["user_input"]}]},
                {"role": "model", "parts": [{"text": item["ai_response"]}]}
            ]
        }
        jsonl_lines.append(json.dumps(entry, ensure_ascii=False))

    # ----------------------------------------------------
    # ส่วนที่ 2: ดึงเคส 👎 (Rating = -1)
    # ----------------------------------------------------
    bad_res = supabase.table("feedback_logs").select("user_input, ai_response, reason").eq("rating", -1).execute()
    bad_data = bad_res.data or []
    print(f"🛠 พบเคส 👎 ที่ต้องนำมาแก้ไข: {len(bad_data)} เคส")

    for item in bad_data:
        reason = item.get("reason") or "คำตอบไม่ตรงตามความต้องการของผู้ใช้"
        print(f"🔄 กำลังแก้ไขคำตอบสำหรับเคส: '{item['user_input']}' (เหตุผล: {reason})")
        
        fixed_response = generate_corrected_response(
            client, 
            item["user_input"], 
            item["ai_response"], 
            reason
        )

        if fixed_response:
            entry = {
                "systemInstruction": {"parts": [{"text": base_system_prompt.strip()}]},
                "contents": [
                    {"role": "user", "parts": [{"text": item["user_input"]}]},
                    {"role": "model", "parts": [{"text": fixed_response}]}
                ]
            }
            jsonl_lines.append(json.dumps(entry, ensure_ascii=False))
            time.sleep(1)

    # ----------------------------------------------------
    # บันทึกลงไฟล์ .jsonl
    # ----------------------------------------------------
    if jsonl_lines:
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(jsonl_lines))
        print(f"\n🎉 สำเร็จ! รวมข้อมูลทั้งหมด {len(jsonl_lines)} ตัวอย่าง ลงไฟล์ '{filename}' เรียบร้อยแล้ว")
    else:
        print("\n⚠️ ยังไม่มีข้อมูล Feedback ในฐานข้อมูล")

if __name__ == "__main__":
    export_feedback_to_jsonl()