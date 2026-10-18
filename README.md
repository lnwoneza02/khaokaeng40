# ข้าวแกง 40
แอป Streamlit สำหรับวางแผนเมนู เก็บสูตรจากร้านและลิงก์ภายนอก และคำนวณต้นทุนถุง/ข้าวราดแกง

## Deploy
1. สร้าง GitHub repository และอัปโหลด `app.py`, `requirements.txt` (และ README นี้)
2. ไปที่ https://share.streamlit.io/ และเลือก Create app > Deploy a public app from GitHub
3. เลือก repository, branch `main`, main file `app.py` แล้ว Deploy

## ข้อจำกัดเวอร์ชันแรก
ข้อมูลที่แก้ไขเก็บใน Streamlit Session State เท่านั้น จึงไม่ถาวรเมื่อรีสตาร์ตหรือหมดเซสชัน ใช้ปุ่มดาวน์โหลด JSON สำรองและนำเข้าภายหลัง อย่าเก็บข้อมูลสำคัญโดยไม่สำรอง สูตรออนไลน์เป็นการเก็บลิงก์ ไม่ได้ดึงเนื้อหาอัตโนมัติ
