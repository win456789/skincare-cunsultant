import streamlit as st
from supabase import create_client, Client

# ดึงค่า URL และ Key จาก Secrets ของ Streamlit
try:
    SUPABASE_URL = st.secrets.get("SUPABASE_URL") or st.secrets.get("NEXT_PUBLIC_SUPABASE_URL") or "https://uwdqzrcwimlrgabisimt.supabase.co"
    SUPABASE_KEY = st.secrets.get("SUPABASE_KEY") or st.secrets.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY") or "sb_publishable_6UoRznS-PFI4GzsAMptu8A_F3jwjh6D"
except Exception:
    SUPABASE_URL = "https://uwdqzrcwimlrgabisimt.supabase.co"
    SUPABASE_KEY = "sb_publishable_6UoRznS-PFI4GzsAMptu8A_F3jwjh6D"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 1. ฟังก์ชันจัดการ User Profile (Supabase)
# ==========================================
def get_all_usernames(device_id="default_device"):
    res = supabase.table("users").select("name").eq("device_id", device_id).execute()
    return [row["name"] for row in res.data]

def save_or_update_user(device_id, name, skin_type, skin_concerns, allergies):
    data = {
        "device_id": device_id,
        "name": name,
        "skin_type": skin_type,
        "skin_concerns": skin_concerns,
        "allergies": allergies
    }
    supabase.table("users").upsert(data, on_conflict="device_id, name").execute()

def get_user_profile(device_id, name):
    res = supabase.table("users").select("skin_type, skin_concerns, allergies").eq("device_id", device_id).eq("name", name).execute()
    if res.data:
        row = res.data[0]
        return {"skin_type": row["skin_type"], "skin_concerns": row["skin_concerns"], "allergies": row["allergies"]}
    return None

def delete_user_profile(device_id, name):
    supabase.table("users").delete().eq("device_id", device_id).eq("name", name).execute()

# ==========================================
# 2. ฟังก์ชันจัดการ Database สินค้า (Supabase)
# ==========================================
def get_all_products_context():
    try:
        res = supabase.table("products").select("brand, name, category, suitable_skin, active_ingredients, price, image_url, purchase_channel").execute()
        rows = res.data
        if not rows:
            return "ไม่มีสินค้าอยู่ในคลัง", 0

        catalog_text = "\n\n=== [คลังสินค้าสกินแคร์ที่อนุญาตให้แนะนำได้เท่านั้น] ===\n"
        for idx, r in enumerate(rows, 1):
            channel = r.get("purchase_channel") or "ไม่ระบุ"
            catalog_text += f"{idx}. แบรนด์: {r['brand']} | ชื่อสินค้า: {r['name']} | หมวดหมู่: {r['category']} | สภาพผิวที่เหมาะ: {r['suitable_skin']} | สารสำคัญ: {r['active_ingredients']} | ราคา: {r['price']} บาท | Image_URL: {r['image_url']} | ช่องทางซื้อ: {channel}\n"
        
        catalog_text += "======================================================\n"
        return catalog_text, len(rows)
    except Exception as e:
        return f"เกิดข้อผิดพลาด: {e}", 0

def clear_products_table():
    """ล้างข้อมูลสินค้าทั้งหมดใน Supabase เพื่อป้องกันข้อมูลซ้ำ"""
    supabase.table("products").delete().neq("id", 0).execute()
    print("🧹 ล้างข้อมูลสินค้าเดิมใน Supabase เรียบร้อยแล้ว!")

def add_new_product(name, brand, category, suitable_skin, active_ingredients, price, description, image_url, purchase_channel="ไม่ระบุ"):
    data = {
        "name": name,
        "brand": brand,
        "category": category,
        "suitable_skin": suitable_skin,
        "active_ingredients": active_ingredients,
        "price": price,
        "description": description,
        "image_url": image_url,
        "purchase_channel": purchase_channel
    }
    supabase.table("products").insert(data).execute()
    print(f"✅ บันทึกสินค้า '{name}' ลง Supabase เรียบร้อยแล้ว")

# ==========================================
# 3. ส่วนรันเพิ่มข้อมูลสินค้าลง Supabase
# ==========================================
if __name__ == "__main__":
    # ล้างข้อมูลเดิมใน Supabase ก่อนเริ่มเพิ่มสินค้า
    clear_products_table()

    add_new_product(
        "CeraVe Foaming Facial Cleanser",
        "CeraVe",
        "Cleanser",
        "ผิวมัน, ผิวผสม, ผิวปกติ",
        "Niacinamide, Ceramides, Hyaluronic Acid",
        485.00,
        "เจลล้างหน้าทำความสะอาดล้ำลึก ควบคุมความมัน ไม่ทำให้ผิวแห้งตึง",
        "https://medias.watsons.co.th/publishing/WTCTH-275385-front-zoom.jpg?version=1733513586&imageresize=1280_1280",
        "https://s.shopee.co.th/AUuUG6GBUn"
    )

    add_new_product(
        "La Roche-Posay Effaclar Serum",
        "La Roche-Posay",
        "Serum",
        "ผิวมัน, ผิวเป็นสิวง่าย",
        "Salicylic Acid, LHA, Glycolic Acid, Niacinamide",
        1300.00,
        "เซรั่มสลายสิวอุดตัน ลดรอยดำจากสิว เหมาะกับ T-zone",
        "https://s2.konvy.com/static/team/2020/1027/16037906661187.jpg",
        "https://s.shopee.co.th/905gTNZWWF"
    )

    add_new_product(
        "MizuMi Water Serum Sunscreen SPF50+",
        "MizuMi",
        "Sunscreen",
        "ทุกสภาพผิว, ผิวแพ้ง่าย, ผิวแห้ง",
        "Physical Sunscreen Filter",
        890.00,
        "กันแดดสูตรน้ำ คุมมัน ไม่เหนอะหนะ ปราศจากสารเคมีทำร้ายผิว",
        "https://s2.konvy.com/static/team/2026/0220/17715725746988.jpg",
        "https://s.shopee.co.th/905gTNZWWF"
    )

    add_new_product(
        "Hada Labo Hydrating Lotion",
        "Hada Labo",
        "Toner",
        "ผิวแห้ง, ผิวขาดน้ำ",
        "Hyaluronic Acid (4 ขนาด)",
        520.00,
        "น้ำตบเพิ่มความชุ่มชื้นล้ำลึก ช่วยให้ผิวนุ่มอิ่มน้ำ",
        "https://medias.watsons.co.th/publishing/WTCTH-217973-front-zoom.jpg?version=1733481450&imageresize=720_720",
        "https://s.shopee.co.th/2qV384nfQc"
    )

    add_new_product(
        "MizuMi Cica Soothing Moisture Gel",
        "MizuMi",
        "Moisturizer",
        "เหมาะเฉพาะผิวมัน, เป็นสิวง่าย",
        "Madagascar Cica 2%, Aloe Vera Extract 99.5%, Carbohydrate Complex, Bio-P Exopolysaccharide",
        690.00,
        "ช่วยปลอบประโลมผิว ลดการระคายเคือง และฟื้นฟูผิวให้แข็งแรง",
        "https://s2.konvy.com/static/team/2023/0209/16759294666766.jpg",
        "https://s.shopee.co.th/9fLNGf44sj"
    )

    add_new_product(
        "Physiogel Soothing Care A.I.",
        "Physiogel",
        "Moisturizer",
        "ผิวแห้ง, ผิวแห้งมาก, ผิวแพ้ง่าย",
        "Palmitamide MEA, BioMimic Technology, Squalane & Betaine, Hydrogenated Lecithin, Olive Oil",
        970.00,
        "ปลอบประโลมผิวและลดปัญหาผิวแห้ง ที่ทำให้ผิวแดงและคัน สำหรับผิวแห้งมากที่ไวต่อการระคายเคือง ช่วยลดผิวแห้ง ให้ความชุ่มชื้น",
        "https://www.fascino.co.th/img/600/744/resize/1/7/176184_1.jpg",
        "https://s.shopee.co.th/30oTKUVUes"
    )

    add_new_product(
        "THE ORDINARY Niacinamide 10% + Zinc 1%",
        "THE ORDINARY",
        "Serum",
        "ผิวเป็นสิว",
        "Niacinamide 10%, Zinc 1%",
        670.00,
        "เซรั่มอเนกประสงค์สำหรับผิวมันที่มีแนวโน้มเป็นสิว ปรับผิวเรียบเนียนและกระจ่างใส Niacinamide 10% + Zinc 1% สูตรที่มีเบสจากน้ำ บูสต์ผิวกระจ่างใส ปรับผิวเรียบเนียนและเสริมสร้างความสมบูรณ์ของปราการผิวเมื่อใช้อย่างต่อเนื่องส่วนผสมเข้มข้นจากไนอะซินาไมด์ (วิตามินบี 3) และซิงค์ พีซีเอ",
        "https://image-optimizer-th.production.sephora-asia.net/images/product_images/closeup_1_Product_769915195958-The-Ordinary-Niacinamide-10-Zinc-1-60_d978166cea0993734e2241daf48efef99c26d7d8_1734426253.png",
        "https://s.shopee.co.th/7faItB3c5J"
    )

    add_new_product(
        "THE ORDINARY Alpha Arbutin 2% + HA",
        "THE ORDINARY",
        "Serum",
        "ผิวหมองคล้ำ, รอยสิว, สีผิวไม่สม่ำเสมอ, จุดด่างดำ",
        "Alpha Arbutin 2%, HA",
        590.00,
        "ลดฝ้า กระ จุดด่างดำ รอยสิวต่างๆจางเร็วขึ้น ช่วยให้ผิวกระจ่าง มีออร่า ผิวใสขึ้น",
        "https://vitaminism.com/wp-content/uploads/2021/08/TO-014a.jpg",
        "https://s.shopee.co.th/1ArkkjL3q"
    )

    add_new_product(
        "The ORDINARY Glycolic Acid 7%",
        "THE ORDINARY",
        "Toner",
        "ไม่เหมาะผิวเบาะบาง,ผลัดเซลล์ผิว",
        "Glycolic Acid 7%",
        600.00,
        "ช่วยปรับสภาพผิวให้เรียบเนียนขึ้นอย่างชัดเจน ช่วยให้สีผิวแลดูสม่ำเสมอยิ่งขึ้น ผิวแลดูกระจ่างใสขึ้นเมื่อใช้เป็นประจำ นอกจากนี้ยังช่วยลดเลือนเส้นริ้วเล็ก ๆ และร่องลึก โทนเนอร์สูตรน้ำนี้ี่เหมาะสำหรับใช้เป็นประจำทุกวัน",
        "https://www.caretobeauty.com/cdn-cgi/image/width=1600,height=1600,f=auto/media/catalog/product//t/h/the-ordinary-glycolic-acid-7-exfoliating-toner-100ml_2_1.jpg",
        "https://s.shopee.co.th/6VOLV3Y361"
    )

    add_new_product(
        "THE ORDINARY saccharomyces ferment 30 milky toner",
        "THE ORDINARY",
        "Toner",
        "เหมาะสำหรับผิวเบาะบาง, ผลัดเซลล์ผิว, ชุ่มชื้น",
        "saccharomyces ferment 30%",
        800.00,
        "ทนเนอร์ที่ช่วยขจัดเซลล์ผิวเสื่อมสภาพอย่างอ่อนโยน ช่วยให้ผิวแลดูเรียบเนียนกระจ่างใสขึ้น พร้อมทั้งช่วยเพิ่มความชุ่มชื้นให้ผิว เหมาะสำหรับผิวแพ้ง่าย",
        "https://image-optimizer-th.production.sephora-asia.net/images/product_images/closeup_1_Product_769915233551-The-Ordinary-Saccharomyces-Ferment-30_fe8037f921d8ba6f88dedb41c0c9a80e25eacf1e_1734426204.png",
        "https://s.shopee.co.th/gQYYXO3Yt"
    )

    add_new_product(
        "SIBLING Daily Skin Detox Gel Cleanser",
        "SIBLING",
        "Cleanser",
        "ผิวมัน, ผิวแห้ง, ผิวปกติ, ผิวแพ้ง่าย, ผิวผสม",
        "Cress Sprout Extract, Chamomile Water, Green Tea Extract, Vitamin C GOA",
        390.00,
        "เจลทำความสะอาดผิวหน้า สูตรอ่อนโยน เหมาะสำหรับทุกสภาพผิวค่า pH Balance ช่วยคงสมดุลผิวหนัง ลดการสะสมของแบคทีเรียและความมันส่วนเกิน",
        "https://siblingth.com/wp-content/uploads/2023/01/Daily-cleansing-tube.png",
        "https://s.shopee.co.th/6fhlhdyqqh"
    )

    add_new_product(
        "AMT Light Emulsion",
        "AMT",
        "Moisturizer",
        "ผิวมัน, ผิวผสม, ผิวเป็นสิว",
        "น้ำมันเมล็ดแมคคาเดเมีย, น้ำมันอะมิโน, Niacinamide, Phosphatidylcholine",
        980.00,
        "ด้วยการมอบสมดุลน้ำและน้ำมันให้แก่ผิวอย่างล้ำลึก ถูกออกแบบให้มีสัดส่วนของน้ำมันภายใน และภายนอกที่เหมาะสมกับผิวแต่ละประเภท ด้วย AMT Oil Balancing Formulation พร้อมส่งมอบคุณประโยชน์ของส่วนผสมต่าง ๆ ด้วยการนำส่งรูปแบบเฉพาะของ AMT",
        "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQu_b6HANSDrRuGDfJUEnBj4ztn8HTXXPGhWRziJMAUrXDUjEHW-7TKc9U&s=10",
        "https://s.shopee.co.th/40h0WoXAPq"
    )

    add_new_product(
        "AMT Purifying & Moisturizing Mild Facial Gel Cleanser",
        "AMT",
        "Cleanser",
        "ผิวแห้ง, ผิวเบาะบาง, ผิวผสม, ผิวเป็นสิว, ผิวแพ้ง่าย",
        "Water, Butylene Glycol, Glycerin, Lauryl Betaine, TEA-Lauroyl/Myristoyl Aspartate, Tremella Fuciformis Polysaccharide, Hydrolyzed Corn Starch, Pelargonium Graveolens (Rose Geranium) Flower Oil, Phenoxyethanol, Citric acid, Disodium EDTA",
        450.00,
        "เปิดประสบการณ์ล้างหน้าแบบใหม่ ด้วยสัมผัส เนื้อเจลลี่ นุ่ม ลื่น ที่เปลี่ยนการล้างหน้าให้เป็นช่วงเวลาที่ผิวได้รับการดูแลอย่างอ่อนโยน",
        "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT0evV9xz5o5Vzqa0yrGuCpsLA8MqEyMdZYKX5JSstUX_n-kXKR4lX7bfF5&s=10",
        "https://s.shopee.co.th/5fpEVuhPHy"
    )

    add_new_product(
        "L'Oréal Paris UV Defender Invisible Resist SPF50+ PA++++",
        "L'Oréal",
        "Sunscreen",
        "โดนแดดแรง, ทุกสภาพผิว",
        "SPF50+ PA++++ filters, Netlock Technology, Daily broad-spectrum system",
        599.00,
        "กันแดดผิวหน้าที่ช่วยปกป้องรังสี UV และ Long UVA พร้อมเนื้อบางเบารู้สึกเหมือนล่องหน เหมาะสำหรับคนที่ต้องการการปกป้องสูงแต่สบายผิวทุกวัน",
        "https://www.konvy.com/static/team/2025/1111/17628584115791_600x600.jpg",
        "https://s.shopee.co.th/8KpzgrOgge"
    )

    add_new_product(
        "HER HYNESS UV ADAPT SUNSCREEN SPF50+PA++++",
        "HER HYNESS",
        "Sunscreen",
        "ไม่โดนแดดแรง, ผิวแพ้ง่าย",
        "SMART UV ADAPT™, Advanced Encapsulated UV Filter",
        1100.00,
        "กันแดดเนื้อเซรั่ม กันเหงื่อ กันแดดได้นานขึ้นถึง 6 ชั่วโมง เพื่อผิวแพ้ง่าย",
        "https://media.allaboutyou.co.th/media/catalog/product/cache/68bd2c830b15d292727e06e369c4931c/8/8/8859572802053.jpg",
        "https://s.shopee.co.th/qjyl7XbUW"
    )

    add_new_product(
        "SRICHAND กันแดดสกินแคร์ สูตรคุมมันคุมสิว ซันลูชั่น แอคเน่",
        "SRICHAND",
        "Sunscreen",
        "ผิวมัน, ผิวเป็นสิว,แดดปกติ",
        "Salicylic Acid Sphere, Gluconolactone, Natural Mineral Marine Wate",
        598.00,
        "กันแดดสูตรแอคเน่แคร์ ช่วยปกป้องผิวจากรังสี UVA และ UVB เนื้อบางเบาเกลี่ยง่าย ลดความมันส่วนเกิน ล้างออกง่าย",
        "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcROWKbVyk1VI534QnBo2QxHPpM3hT4zRTDqeibT5bLJ3UWicTdil00f6ZhK&s=10",
        "https://s.shopee.co.th/70Kc6UeBd2"
    )

    add_new_product(
        "Anessa Perfect UV Sunscreen Skincare Milk NA SPF50+ PA++++",
        "Anessa",
        "Sunscreen",
        "ผิวมัน, แดดแรง, กันน้ำ",
        "Green tea extract, Potentilla Erecta Root Extract, Collagen, Super Hyaluronic acid, Glycerin,High-fructose corn syrup, Dipotassium glycyrrhizate",
        425.00,
        "เพอร์เฟค ยูวี ซันสกรีน สกินแคร์ มิลค์ เอ็นเอ เอสพีเอฟ 50+ พีเอ++++กันแดดเนื้อน้ำนม บางเบา ซึมซาบเร็ว สำหรับผิวหน้า ปกป้องผิวจากรังสี UVพร้อมลดเลือนจุดด่างดำ ฝ้าแดด เผยผิวสวย ฉ่ำโกล์ว ชุ่มชื้นยาวนาน 8 ชั่วโมง",
        "https://s2.konvy.com/static/team/2026/0327/17746071957932_600x600.jpg",
        "https://s.shopee.co.th/4qG7WZhS02"
    )

    add_new_product(
        "Senka Perfect Whip Acne Care F",
        "Senka",
        "Cleanser",
        "ผิวมัน, ผิวเป็นสิว",
        "Water, Stearic acid, Myristic acid, PEG-8, Potassium Hydroxide, Lauric Acid, Glycerin, Dipropylene Glycol, Alcohol, Salicylic Acid, Beeswax, Polyquaternium-7, Fragrance, Disodium EDTA, PEG-90M, Sodium Benzoate, Sodium Metabisulfite, Sodium Metaphosphate, PEG/PPG-14/7 Dimethyl Ether, Sodium Hyaluronate, Butylene Glycol, Sericin, Citric acid, Potassium Sorbate, Sodium Acetylated Hyaluronate, BHT, Silica, Chamomilla Recutita Flower Extract, CI 77288, CI 77491, CI 77492",
        199.00,
        "วิปโฟมสำหรับผิวเป็นสิว ลดโอกาสการเกิดสิวใน 4 สัปดาห์* ทำความสะอาดสิ่งสกปรกที่อุดตัน ความมัน เซลล์ผิวชั้นนอกที่เสื่อมสภาพ ด้วยซาลิไซลิก แอซิด ดูแลผิวที่มีปัญหาสิว มอบผิวสะอาดใส ลดแบคทีเรีย สาเหตุหนึ่งของการเกิดสิว เผยผิวสวยสุขภาพดี ด้วย เกียวโต คาโมมายล์ เอ็กซ์แทร็กซ์ ช่วยแอนตี้ออกซิแดนท์ มอบความชุ่มชื่นและเนียนนุ่มให้แก่ผิว*จากผลทดสอบทางคลินิก ในกลุ่มตัวอย่าง 30 คน โดย CIDP PTE LTD ประเทศสิงคโปร์ ",
        "https://medias.watsons.co.th/publishing/WTCTH-282638-front-zoom.jpg?version=1786217578&imageresize=720_720",
        "https://s.shopee.co.th/9AP6galBsv"
    )

    add_new_product(
        "Cetaphil Gentle Skin Cleanser",
        "Cetaphil",
        "Cleanser",
        "ผิวแพ้ง่าย, เป็นสิว, ผิวธรรมดา, ผิวแห้ง",
        "purified water, cetyl alcohol, propylene glycol, sodium lauryl sulfate, stearyl alcohol, methy hydroxybenzoate, propyl hydroxybenzoate, butyl hydroxybenzoate",
        690.00,
        "ผลิตภัณฑ์ยอดนิยมสูตรเฉพาะของเซตาฟิลที่ได้รับรางวัลมากมายจากกูรูด้านความสวยความงาม เพราะมีสูตรที่อ่อนโยน ปราศจากสบู่ และน้ำหอม สามารถใช้เป็นประจำได้ทุกวันไม่ระคายเคืองผิว ล้างออกง่าย คงความชุ่มชื้น ทำให้ผิวอ่อนนุ่ม เรียบ และแข็งแรง สามารถใช้ทำความสะอาดได้แม้กระทั่งผิวของทารก- เหมาะสำหรับทุกสภาพผิวแม้ผิวบอบบาง- เหมาะกับการใช้ทั้งผิวหน้าและผิวกาย- pH Balance ใกล้เคียงผิวหนังตามธรรมชาติ- ให้ผิวนุ่มชุ่มชื่นไม่แห้งตึงหลังล้างหน้าด้วย Moisturizing Film- ทำความสะอาดง่ายและสะดวก โดยใช้น้ำหรือไม่ใช้น้ำก็ได้- Non-comedogenic, Hypoallergenic tested",
        "https://medias.watsons.co.th/publishing/WTCTH-262634-front-zoom.jpg?version=1733517519&imageresize=720_720",
        "https://s.shopee.co.th/9fLNHbJYhs"
    )

    add_new_product(
        "Neutrogena Deep Clean Acne Foaming Cleanser",
        "Neutrogena",
        "Cleanser",
        "ผิวมัน, ผิวเป็นสิวง่าย, ผิวผสม, ผิวแพ้ง่าย",
        "Water,Glycerin, Sodium Cocoyl Glycinate,Sodium Cocoyl Isethionate, Cocamidopropyl Betaine, Myristic Acid,Glycol Distearate, Acrylates Copolymer,Lauric Acid, PEG-120 Methyl Glucose Dioleate, Phenoxyethanol,Salicyluc Acid, Caprylyl Glycol, Chlorphenesin, Fragance,Sodium Hydroxide, Hydroxyethycellulose,o-Cymen-5-ol, Disocium EDTA",
        209.00,
        "การล้างหน้าด้วยวิปโฟมที่มีสบู่ เป็นการทำร้ายผิวโดยไม่รู้ตัว เพราะสบู่มีค่าความเป็นด่างสูง จึงทำให้ปราการผิวอ่อนแอ จึงป้องกันแบคทีเรีย และ ปัจจัยทำร้ายผิวได้น้อยลง",
        "https://medias.watsons.co.th/publishing/WTCTH-295257-front-zoom.jpg?version=1733776460&imageresize=720_720",
        "https://s.shopee.co.th/2BFMM0crbl"
    )

    add_new_product(
        "Eucerin HYALURON RADIANCE-LIFT FILLER 3D SERUM",
        "Eucerin",
        "Serum",
        "ริ้วรอย, จุดด่างดำ, ผิวผู้สูงอายุ",
        "Glycerin",
        3450.00,
        "เซรั่มบำรุงผิวหน้า ลดเลือนริ้วรอย ยกกระชับ นวัตกรรมเซรั่มลดริ้วรอยอายุ 40+ ช่วยลดจุดด่างดำตามวัย และฟื้นบำรุงปัญหาผิวได้แบบ 3 มิติ",
        "https://www.konvy.com/static/team/2024/0201/17067774604959_600x600.jpg",
        "https://s.shopee.co.th/40h0XR4pgW"
    )

    add_new_product(
        "Eucerin HYALURON-FILLER + ELASTICITY NIGHT CREAM",
        "Eucerin",
        "Moisturizer",
        "ริ้วรอย, จุดด่างดำ, ผิวผู้สูงอายุ, ใช้สำหรับกลางคืนเท่านั้น",
        "Thiamidol, กรดไฮยาลูรอนิก",
        3050.00,
        "ผลิตภัณฑ์บำรุงผิวหน้า สูตรกลางคืน สำหรับทุกสภาพผิว นวัตกรรมเพื่อการฟื้นบำรุงปัญหาผิวแก้ยากจากวัย เพื่อผิวดูอ่อนเยาว์กระจ่างใส",
        "https://down-th.img.susercontent.com/file/1c2f369cf94e7e9101fea9911a4640e7",
        "https://s.shopee.co.th/7VGshu0BgB"
    )

    add_new_product(
        "Eucerin HYALURON-FILLER + ELASTICITY DAY CREAM SPF30",
        "Eucerin",
        "Moisturizer",
        "ริ้วรอย, จุดด่างดำ, ผิวผู้สูงอายุ, ใช้สำหรับตอนเช้าเท่านั้น",
        "Thiamidol, กรดไฮยาลูรอนิก",
        2800.00,
        "นวัตกรรมเพื่อการฟื้นบำรุงปัญหาผิวแก้ยากจากวัย เพื่อผิวดูอ่อนเยาว์กระจ่างใส ผิวยืดหยุ่นกระชับแน่น ด้วย Collagen-Elastin Complex ที่ช่วยคืนความยืดหยุ่น ให้ผิวดูกระชับ แม้ผิวหย่อนคล้อยมาก จุดด่างดำดูจางลง เห็นผลใน 2 สัปดาห์ ด้วย Thiamidol สารช่วยลดจุดด่างดำทรงประสิทธิภาพ ริ้วรอยดูจางลง ด้วยไฮยาลูรอนโมเลกุลขนาดใหญ่และไฮยาลูรอนโมเลกุลขนาดเล็กที่ช่วยเติมริ้วรอยลึก",
        "https://obs-ect.line-scdn.net/r/ect/ect/cj0tNWdjZmF2dWVscW1qbiZzPWpwNiZ0PW0mdT0xZnZiNGZpNDQ0ZWcwJmk9MA",
        "https://s.shopee.co.th/2qV39LKzDX"
    )

    add_new_product(
        "Hada Labo Anti-Aging Lotion",
        "Hada Labo",
        "Toner",
        "ริ้วรอย, จุดด่างดำ, ฝ้าและกระ, ผิวผู้สูงอายุ",
        "Water, Butylene Glycol, Glycerin, Diglycerin, Squalane, PEG-20 Sorbitan Isostearate, Caprylic/Capric Triglyceride, Methylparaben, Limnanthes Alba (Meadowfoam) Seed Oil, PPG-10 Methyl Glucose Ether, Phytosteryl/Octyldodecyl Lauroyl Glutamate, Carbomer, Triethanolamine, Pullulan, Polyacrylate Crosspolymer-11, Phytosteryl Macadamiate, Hydroxyethyl Acrylate/Sodium Acryloyldimethyl Taurate Copolymer, Xanthan Gum, Disodium EDTA, Isohexadecane, Sodium Hyaluronate, Lactobacillus/Soymilk Ferment Filtrate, Polysorbate 60, Polyquaternium-51, Sorbitan Isostearate, Hydrolyzed Collagen, Sodium Acetylated Hyaluronate, Hydrolyzed Hyaluronic Acid, Ammonium Acrylates Copolymer, Phenoxyethanol, Hydrolyzed Elastin",
        670.00,
        "โลชั่นสูตรใหม่ล่าสุดจากญี่ปุ่น เพิ่มประสิทธิภาพเพื่อดูแลถึงระดับเซลล์ผิว ช่วยเพิ่มความชุ่มชื่น ฟื้นฟูผิวที่มีปัญหาริ้วรอยและความหย่อนคล้อยโดยเฉพาะ Elasgrow* ส่วนผสมลิขสิทธิ์เฉพาะของฮาดะ ลาโบะ มีขนาดโมเลกุลเล็กช่วยเพิ่มประสิทธิภาพการสร้าง Elastin เพื่อยึดเกาะ Collagen ในเซลล์ผิวไว้ด้วยกัน ทำให้ผิวยืดหยุ่นและกระชับล้ำลึกถึงผิวชั้นใน Soymilk Ferment Filtrate อุดมไปด้วยไอโซฟลาโวน มีโมเลกุลเล็กจึงแทรกซึมเข้าไปเพิ่มความกระชับให้กับผิวได้ล้ำลึกยิ่งขึ้น 3D Hyaluronic Acid ชนิดพิเศษ เมื่อซึมเข้าสู่ผิวจะสร้างตาข่ายโอบอุ้มและกักเก็บความชุ่มชื่นไว้กับผิวได้นานกว่าHyaluronic Acid, Super Hyaluronic Acid และ Nano Hyaluronic Acid ทำงานร่วมกับ 3D Hyaluronic Acid ช่วยเติมเต็มความชุ่มชื่นให้ผิวเนียนนุ่ม อิ่มน้ำเนื้อโลชั่นเข้มข้นแต่ซึมซาบเร็ว เหมาะที่จะใช้ในขั้นตอนแรกหลังล้างหน้า ช่วยปรับสมดุลผิวให้พร้อมเปิดรับการบำรุง มอยส์เจอไรเซอร์ที่ใช้ตามมาจะซึมเข้าสู่ผิวได้ดีขึ้นสูตรอ่อนโยน ไม่ระคายเคืองผิว เพราะไม่มีส่วนผสมของแอลกอฮอล์ น้ำมันแร่ น้ำหอม และสี",
        "https://s2.konvy.com/static/team/2023/0509/2023050913294852354.jpg",
        "https://s.shopee.co.th/7faIuHkKls"
    )

    add_new_product(
        "ANTHELIOS UVMUNE400+ ANTI-DARK SPOTS FLUID SPF50+",
        "la roche posay",
        "Sunscreen",
        "ฝ้าและกระ, จุดด่างดำ, ผิวไม่สม่ำเสมอ, ผิวหมองคล้ำง่าย",
        "Mexoryl400, Uvinul A+, Avobenzone, Mexoryl SX, Mexoryl XL, Tinosorb S, Uvinul T150",
        1199.00,
        "สารกันแดดที่ครอบคลุม (ยาวถึง Ultra Long UVA) เทคโนโลยีเนื้อสัมผัส และการเกาะติดผิว (Netlock) รวมถึง Active ในการบำรุงผิวงานวิจัยแน่น (แถบม่วงมี Melasyl™ จัดการเม็ดสีที่ต้นตอ) เรียกว่าไว้ใจได้ว่าผิวเราจะได้รับการปกป้องได้จริง และมาในค่าตัวที่สมเหตุสมผล",
        "https://inwfile.com/s-cj/n134pw.jpg",
        "https://s.shopee.co.th/113Oy7NduW"
    )

    add_new_product(
        "SKIN1004 Madagascar Centella Ampoule",
        "Centella",
        "Serum",
        "ผิวแพ้ง่าย, ผิวเป็นสิวง่าย, ผิวอ่อนแอ, ผิวระคายเคือง",
        "Centella Asiatica Extract (100% pure Madagascar origin), water, Glycerin, Butylene Glycol, 1,2-Hexanediol, Cellulose Gum, Ethylhexylglycerin",
        790.00,
        "ช่วยฟื้นบำรุง พร้อมปลอบประโลมผิวให้กลับมาแข็งแรง ด้วยพลังของ Centella สารสกัดบริสุทธิ์จากมาดากัสการ์ และช่วยลดการสะสมของเชื้อแบคทีเรีย ลดรอยดำ รอยแดง ที่เกิดจากสิว ดูแลผิวที่อ่อนแอ พร้อมฟื้นบำรุงผิวให้แข็งแรงสุขภาพดีอย่างอ่อนโยน ค่า pH 5.5 ใกล้เคียงกับผิว ลดโอกาสการเกิดสิว ยับยั้งการเติบโตของแบคทีเรีย ดูแลปัญหาที่เกิดจากรอยสิว สมานแผลให้หายเร็วขึ้น ชะลอการเสื่อมของเซลล์ผิวและลดโอกาสการเกิดริ้วรอย ฟื้นบำรุงเซลล์ผิวให้แข็งแรง อ่อนโยนต่อทุกสภาพผิว ปราศจากพาราเบน, มิเนอรัล ออยล์, แอลกอฮอล์, ซิลิโคน, สีสังเคราะห์ และปราศจากการทดลองกับสัตว์",
        "https://medias.watsons.co.th/publishing/WTCTH-293431-front-zoom.jpg?version=1750274029&imageresize=720_720",
        "https://s.shopee.co.th/8AWZVLRSTr"
    )

    add_new_product(
        "Anessa PERFECT UV MILD MILK NA SPF50+ PA++++",
        "Anessa",
        "Sunscreen",
        "ผิวแพ้ง่าย, ผิวบอบบางแพ้ง่าย, ผิวเด็ก, ทุกสภาพผิว, แดดแรง",
        "Water, Dimethicone, Diisopropyl Sebacate, Butylene Glycol, Caprylyl Methicone, Cetyl Ethylhexanoate",
        1050.00,
        "อเนสซ่า เพอร์เฟค ยูวี ซันสกรีน สกินแคร์ มิลค์ เอ็นเอ เอสพีเอฟ 50+ พีเอ++++ กันแดดสูตรเนื้อน้ำนมบางเบา ซึมซาบเร็ว ช่วยลดเลือนจุดด่างดำ",
        "https://www.central.co.th/_next/image?url=https%3A%2F%2Fassets.central.co.th%2Ffile-assets%2FCDSPIM%2Fweb%2FImage%2FCDS1927%2FANESSA-ANPERFECTUVMILDMILK60ML-CDS19271460-1.webp&w=256&q=75",
        "https://s.shopee.co.th/3qNaOYCuan"
    )

    print("✨ บันทึกสินค้าลง Supabase สำเร็จทั้งหมด 27 รายการเรียบร้อย!")