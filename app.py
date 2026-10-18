import copy
import json
import random
from datetime import date, timedelta
from urllib.parse import quote, urlparse
import xml.etree.ElementTree as ET

import requests
import streamlit as st

st.set_page_config(page_title="ข้าวแกง 40 | เมนูหมุนเวียน", page_icon="🍛", layout="centered")
DEFAULT = [
    {"name":"ผัดพริกแกงปลาดุก","category":"ผัด","source":"สูตรของร้าน","url":"","steps":"","status":"ประจำร้าน"},
    {"name":"ต้มจืดหมูสับ","category":"ต้ม","source":"สูตรของร้าน","url":"","steps":"","status":"ประจำร้าน"},
    {"name":"ผัดกะเพราหมูสับ","category":"ผัด","source":"สูตรของร้าน","url":"","steps":"","status":"ประจำร้าน"},
    {"name":"ยำปลาทู","category":"ยำ","source":"สูตรของร้าน","url":"","steps":"","status":"ประจำร้าน"},
    {"name":"แกงกะทิไก่กับยอดมะพร้าว","category":"แกง","source":"สูตรของร้าน","url":"","steps":"","status":"ประจำร้าน"},
]
CATEGORIES = ["ผัด","ต้ม","แกง","ยำ","ทอด","นึ่ง","อื่น ๆ"]
STATUSES = ["ประจำร้าน","รอทดลอง","ขายดี","พักไว้"]


def clean_url(url):
    url = str(url or "").strip()
    p = urlparse(url)
    return url if p.scheme in ("http", "https") and p.netloc else ""


def normalized_menu(obj):
    if not isinstance(obj, dict) or not str(obj.get("name", "")).strip():
        return None
    return {"name":str(obj["name"]).strip()[:120],
            "category":str(obj.get("category", "อื่น ๆ"))[:40],
            "source":str(obj.get("source", "ไม่ระบุ"))[:160],
            "url":clean_url(obj.get("url", "")),
            "steps":str(obj.get("steps", ""))[:10000],
            "status":str(obj.get("status", "ประจำร้าน")) if obj.get("status") in STATUSES else "ประจำร้าน"}


def migrate(obj):
    # รองรับไฟล์สำรอง V1 ซึ่งเป็น list ของเมนู
    if isinstance(obj, list):
        menus = [normalized_menu(x) for x in obj]
        return {"version":2,"menus":[x for x in menus if x],"plan":{}}
    if not isinstance(obj, dict) or not isinstance(obj.get("menus"), list):
        raise ValueError("ไฟล์ต้องเป็น JSON สำรองของข้าวแกง 40 V1 หรือ V2")
    menus = [normalized_menu(x) for x in obj["menus"]]
    menus = [x for x in menus if x]
    if len(menus) > 2000:
        raise ValueError("จำนวนเมนูมากเกินไป")
    names = {x["name"] for x in menus}
    raw_plan = obj.get("plan", {})
    plan = {}
    if isinstance(raw_plan, dict):
        for k, v in raw_plan.items():
            try:
                date.fromisoformat(k)
                if isinstance(v, list):
                    plan[k] = list(dict.fromkeys(x for x in v if isinstance(x,str) and x in names))[:5]
            except (ValueError, TypeError):
                continue
    return {"version":2,"menus":menus,"plan":plan}


def state():
    if "store" not in st.session_state:
        st.session_state.store = {"version":2,"menus":copy.deepcopy(DEFAULT),"plan":{}}
    return st.session_state.store


def export_json():
    return json.dumps(state(), ensure_ascii=False, indent=2).encode("utf-8")


def add_menu(name, category, source, url, steps, status):
    name = name.strip()
    if not name:
        return "กรุณากรอกชื่อเมนู"
    if any(x["name"].casefold() == name.casefold() for x in state()["menus"]):
        return "มีชื่อเมนูนี้ในคลังแล้ว"
    state()["menus"].append(normalized_menu({"name":name,"category":category,"source":source,"url":url,"steps":steps,"status":status}))
    return None


def search_bing_rss(query):
    # ผลลัพธ์ค้นหาสาธารณะ อาจถูกจำกัดโดยผู้ให้บริการ; ไม่ดึงสูตรเต็มอัตโนมัติ
    response = requests.get("https://www.bing.com/search", params={"q":query + " สูตรอาหาร วิธีทำ", "format":"rss", "setlang":"th-TH"}, timeout=9,
                            headers={"User-Agent":"Mozilla/5.0 (compatible; Khaokaeng40/2.0)"})
    response.raise_for_status()
    root = ET.fromstring(response.content)
    items = []
    for item in root.findall("./channel/item")[:12]:
        title = (item.findtext("title") or "").strip()
        link = clean_url(item.findtext("link") or "")
        if title and link:
            items.append({"title":title,"url":link})
    return items


store = state()
menus = store["menus"]
plan = store["plan"]
st.title("🍛 ข้าวแกง 40")
st.caption("V2 • Run เมนูรายวัน 3–5 อย่าง • คลังสูตรภายนอก • ยังไม่คำนวณต้นทุน")
st.info("ข้อมูลบันทึกชั่วคราวในเซสชัน Streamlit เท่านั้น โปรดดาวน์โหลดสำรอง JSON ทุกครั้งหลังแก้ไขสำคัญ ก่อนปิดหรือรีสตาร์ตแอป")
with st.expander("💾 สำรอง / นำเข้าข้อมูล (รองรับ V1 และ V2)"):
    st.download_button("⬇️ ดาวน์โหลดข้อมูลทั้งหมด (เมนู + ตาราง)", export_json(), file_name=f"khaokaeng40_v2_{date.today().isoformat()}.json", mime="application/json")
    uploaded = st.file_uploader("นำเข้า JSON จาก V1 หรือ V2", type=["json"])
    if uploaded and st.button("ยืนยันนำเข้า (แทนที่ข้อมูลปัจจุบัน)"):
        try:
            if uploaded.size > 3_000_000:
                raise ValueError("ไฟล์ใหญ่เกิน 3 MB")
            st.session_state.store = migrate(json.loads(uploaded.getvalue().decode("utf-8")))
            st.success("นำเข้าข้อมูลแล้ว")
            st.rerun()
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            st.error(f"นำเข้าไม่สำเร็จ: {exc}")

t1, t2, t3 = st.tabs(["📅 Run เมนู", "📚 คลังเมนู", "🔎 ค้นหาภายนอก"])
with t1:
    st.subheader("วางแผนเมนู 7–30 วัน")
    start = st.date_input("เริ่มวันที่", value=date.today(), key="start_date")
    days = st.slider("วางแผนกี่วัน", min_value=7, max_value=30, value=7)
    per_day = st.select_slider("เมนูต่อวัน", options=[3,4,5], value=4)
    candidates = [m for m in menus if m["status"] != "พักไว้"]
    if len(candidates) < per_day:
        st.warning(f"มีเมนูพร้อมใช้ {len(candidates)} อย่าง ต้องมีอย่างน้อย {per_day} อย่างก่อนสร้างตาราง")
    seed = st.number_input("หมายเลขชุดสุ่ม (เปลี่ยนเลขเพื่อเปลี่ยนตาราง)", min_value=0, max_value=99999, value=40)
    if st.button("🔄 สร้างตารางหมุนเวียน", type="primary", disabled=len(candidates)<per_day):
        rng = random.Random(int(seed))
        history = []
        for offset in range(days):
            key = (start + timedelta(days=offset)).isoformat()
            chosen = []
            pool = [m["name"] for m in candidates]
            for _ in range(per_day):
                weights = [1 if n in history[-per_day:] else (3 if n in history[-per_day*2:] else 10) for n in pool]
                picked = rng.choices(pool, weights=weights, k=1)[0]
                chosen.append(picked)
                pool.remove(picked)
            plan[key] = chosen
            history.extend(chosen)
        st.success("สร้างตารางแล้ว สามารถแก้ไขแต่ละวันด้านล่าง")
    st.caption("การสร้างตารางใหม่จะเขียนทับแผนในช่วงวันที่เลือก ไม่กระทบวันอื่น ระบบพยายามลดการซ้ำแต่ไม่รับประกันเมื่อมีเมนูน้อย")
    names = [m["name"] for m in candidates]
    for offset in range(days):
        d = start + timedelta(days=offset)
        key = d.isoformat()
        with st.expander(f"{d.strftime('%d/%m/%Y')}  •  {', '.join(plan.get(key, [])) or 'ยังไม่จัดเมนู'}", expanded=(offset==0)):
            current = [x for x in plan.get(key, []) if x in names]
            chosen = st.multiselect("เลือกหรือแก้เมนู 3–5 อย่าง", names, default=current, key=f"pick_{key}")
            if st.button("บันทึกวันนี้", key=f"save_{key}"):
                if 3 <= len(chosen) <= 5:
                    plan[key] = chosen
                    st.success("บันทึกในเซสชันแล้ว")
                    st.rerun()
                else:
                    st.error("ต้องเลือก 3–5 เมนู")
    st.download_button("⬇️ ดาวน์โหลดตาราง CSV", "วันที่,เมนู\n" + "\n".join(f'{(start+timedelta(days=i)).isoformat()},"{ " / ".join(plan.get((start+timedelta(days=i)).isoformat(), [])).replace(chr(34), chr(34)*2) }"' for i in range(days)), file_name="menu_plan.csv", mime="text/csv")

with t2:
    st.subheader("คลังเมนูของร้านและเมนูทดลอง")
    filter_status = st.selectbox("กรองสถานะ", ["ทั้งหมด"] + STATUSES)
    for m in menus:
        if filter_status != "ทั้งหมด" and m["status"] != filter_status:
            continue
        with st.expander(f"{m['name']}  •  {m['status']}"):
            st.write(f"ประเภท: {m['category']} | ที่มา: {m['source']}")
            if m["url"]:
                st.link_button("เปิดสูตรต้นฉบับ", m["url"])
            with st.form("edit_"+str(menus.index(m))):
                category = st.selectbox("ประเภท", CATEGORIES, index=CATEGORIES.index(m["category"]) if m["category"] in CATEGORIES else len(CATEGORIES)-1)
                status = st.selectbox("สถานะ", STATUSES, index=STATUSES.index(m["status"]))
                source = st.text_input("ชื่อแหล่งสูตร / ช่อง", value=m["source"])
                url = st.text_input("ลิงก์สูตร", value=m["url"])
                steps = st.text_area("โน้ตหรือขั้นตอนทำ", value=m["steps"])
                if st.form_submit_button("บันทึกการแก้ไข"):
                    if url.strip() and not clean_url(url):
                        st.error("ลิงก์ต้องขึ้นต้นด้วย https:// หรือ http://")
                    else:
                        m.update(category=category,status=status,source=source,url=clean_url(url),steps=steps)
                        st.success("บันทึกในเซสชันแล้ว")
                        st.rerun()
    st.divider()
    st.subheader("เพิ่มเมนูจากลิงก์เอง")
    with st.form("new_menu", clear_on_submit=True):
        name = st.text_input("ชื่ออาหาร *")
        category = st.selectbox("ประเภท", CATEGORIES)
        source = st.text_input("แหล่งที่มา เช่น YouTube / TikTok / เว็บไซต์")
        url = st.text_input("ลิงก์ต้นฉบับ (ไม่บังคับ)")
        steps = st.text_area("โน้ตสูตรหรือวิธีทำ")
        status = st.selectbox("สถานะ", STATUSES, index=1)
        if st.form_submit_button("➕ เพิ่มเข้าคลัง"):
            if url.strip() and not clean_url(url):
                st.error("ลิงก์ต้องขึ้นต้นด้วย https:// หรือ http://")
            else:
                error = add_menu(name,category,source or "เพิ่มเอง",url,steps,status)
                if error: st.error(error)
                else:
                    st.success("เพิ่มเมนูแล้ว")
                    st.rerun()

with t3:
    st.subheader("ค้นหาเมนูและสูตรจากอินเทอร์เน็ต")
    st.caption("ค้นหาผ่านผลลัพธ์สาธารณะของ Bing RSS เมื่อเข้าถึงได้ และเปิดต้นฉบับก่อนนำสูตรไปใช้ ข้อมูลสูตรเต็มไม่ได้ถูกดึงอัตโนมัติ")
    q = st.text_input("ค้นหา เช่น แกงไก่ ผัดผัก เมนูข้าวแกง", value="เมนูข้าวแกง")
    if st.button("🔎 ค้นหาออนไลน์"):
        if not q.strip():
            st.warning("กรอกคำค้นก่อน")
        else:
            with st.spinner("กำลังค้นหา..."):
                try:
                    st.session_state.results = search_bing_rss(q.strip())
                    if not st.session_state.results:
                        st.warning("ยังไม่พบผลลัพธ์ ลองคำค้นอื่นหรือเปิด Google ด้านล่าง")
                except (requests.RequestException, ET.ParseError, ValueError):
                    st.session_state.results = []
                    st.warning("บริการค้นหาอัตโนมัติไม่ตอบกลับในขณะนี้ ใช้ปุ่มค้นหาผ่านเว็บแทนได้")
    st.link_button("เปิด Google เพื่อค้นสูตร", "https://www.google.com/search?q=" + quote((q or "สูตรอาหารไทย") + " สูตรอาหาร"))
    st.link_button("เปิด YouTube เพื่อค้นสูตร", "https://www.youtube.com/results?search_query=" + quote((q or "อาหารไทย") + " วิธีทำ"))
    results = st.session_state.get("results", [])
    for i, result in enumerate(results):
        with st.container(border=True):
            st.write(f"**{result['title']}**")
            st.link_button("อ่านแหล่งต้นฉบับ", result["url"])
            if st.button("เก็บลิงก์เข้าคลัง", key=f"result_{i}"):
                error = add_menu(result["title"][:120], "อื่น ๆ", "ค้นหาออนไลน์ (ตรวจสอบสูตรก่อน)", result["url"], "", "รอทดลอง")
                if error: st.warning(error)
                else: st.success("เก็บลิงก์แล้ว ไปแก้ชื่อและรายละเอียดได้ในคลังเมนู")
    st.caption("หมายเหตุ: ผลค้นหาอาจไม่ใช่สูตรอาหารทั้งหมด และการบันทึกผลค้นหาเป็นเพียงการเก็บลิงก์ ไม่ได้ยืนยันต้นทุนหรือความเหมาะสมสำหรับขาย")
