import copy
import csv
import io
import json
import random
from datetime import date, timedelta
from urllib.parse import quote, urlparse

import streamlit as st

st.set_page_config(page_title="ข้าวแกง 40 V3", page_icon="🍛", layout="centered")

GROUPS = ["ผัดจืด/ผัดผัก", "ผัดเผ็ด", "แกง", "ต้มจืด", "ยำ", "ผัดไข่"]
STATUSES = ["ประจำร้าน", "รอทดลอง", "ขายดี", "พักไว้"]
# รวม 50 เมนูตัวอย่าง (10 เมนูต่อกลุ่ม 1-4 และ 5 เมนูต่อกลุ่มยำ/ผัดไข่)
SEED_GROUPS = {
    "ผัดจืด/ผัดผัก": ["ผัดกะหล่ำปลีหมูสับ", "ผัดผักรวมมิตร", "ไก่ผัดขิง", "ผัดถั่วงอกเต้าหู้", "ผัดคะน้าหมู", "ผัดดอกกะหล่ำหมู", "ผัดแตงกวาหมูสับ", "ผัดบวบหมูสับ", "ผัดฟักทอง", "ผัดเห็ดรวม"],
    "ผัดเผ็ด": ["ผัดพริกแกงปลาดุก", "ผัดกะเพราหมูสับ", "ผัดพริกแกงไก่", "ผัดเผ็ดหมู", "ผัดฉ่าปลาดุก", "ผัดพริกแกงถั่วฝักยาว", "คั่วกลิ้งหมู", "ผัดเผ็ดไก่หน่อไม้", "ผัดกะเพราไก่", "ผัดพริกหยวกหมู"],
    "แกง": ["แกงกะทิไก่กับยอดมะพร้าว", "แกงเขียวหวานไก่", "แกงฟักทองไก่", "แกงเผ็ดหน่อไม้ไก่", "แกงป่าไก่", "พะแนงหมู", "แกงเทโพ", "แกงเลียง", "แกงส้มผักรวม", "มัสมั่นไก่"],
    "ต้มจืด": ["ต้มจืดหมูสับ", "ต้มจืดเต้าหู้หมูสับ", "ต้มจืดฟักไก่", "ต้มจืดตำลึงหมูสับ", "ต้มจืดวุ้นเส้นหมูสับ", "ต้มจืดกะหล่ำปลี", "ต้มจืดหัวไชเท้ากระดูกหมู", "ต้มจืดมะระยัดไส้", "ต้มจับฉ่าย", "ต้มจืดสาหร่ายเต้าหู้"],
    "ยำ": ["ยำปลาทู", "ยำไข่ต้ม", "ยำวุ้นเส้น", "ยำเห็ดรวม", "ยำปลากระป๋อง"],
    "ผัดไข่": ["ผัดบวบใส่ไข่", "ผัดวุ้นเส้นใส่ไข่", "ผัดมะเขือยาวใส่ไข่", "ผัดฟักทองใส่ไข่", "ผัดมะระใส่ไข่"],
}
SHOP = {"ผัดพริกแกงปลาดุก", "ต้มจืดหมูสับ", "ผัดกะเพราหมูสับ", "ยำปลาทู", "แกงกะทิไก่กับยอดมะพร้าว"}
OLD_MAP = {"ผัด": "ผัดเผ็ด", "ต้ม": "ต้มจืด", "แกง": "แกง", "ยำ": "ยำ"}


def valid_url(value):
    value = str(value or "").strip()
    parsed = urlparse(value)
    return value if parsed.scheme in ("https", "http") and parsed.netloc else ""


def seed_menus():
    return [{"name": name, "category": group, "status": "ประจำร้าน" if name in SHOP else "รอทดลอง",
             "source": "สูตรของร้าน" if name in SHOP else "ไอเดียเมนูเริ่มต้น (ยังไม่ตรวจสูตร)", "url": "", "steps": ""}
            for group, names in SEED_GROUPS.items() for name in names]


def fix_menu(row):
    if not isinstance(row, dict) or not str(row.get("name", "")).strip():
        return None
    cat = str(row.get("category", "")).strip()
    cat = OLD_MAP.get(cat, cat)
    if cat not in GROUPS:
        cat = "ผัดจืด/ผัดผัก"  # ให้ผู้ใช้ตรวจหมวดที่ย้ายมาจาก V1/V2
    status = row.get("status", "รอทดลอง")
    return {"name": str(row["name"]).strip()[:120], "category": cat,
            "source": str(row.get("source", "เพิ่มเอง"))[:160],
            "url": valid_url(row.get("url", "")), "steps": str(row.get("steps", ""))[:10000],
            "status": status if status in STATUSES else "รอทดลอง"}


def store():
    if "data_v3" not in st.session_state:
        st.session_state.data_v3 = {"version": 3, "menus": seed_menus(), "plan": {}}
    return st.session_state.data_v3


def migrate(raw):
    if isinstance(raw, list):  # V1
        old = raw
        rawplan = {}
    elif isinstance(raw, dict) and isinstance(raw.get("menus"), list):
        old = raw["menus"]
        rawplan = raw.get("plan", {})
    else:
        raise ValueError("ต้องเป็นไฟล์ JSON ข้าวแกง 40 รุ่น V1, V2 หรือ V3")
    if len(old) > 2000:
        raise ValueError("จำนวนเมนูมากเกินไป")
    combined = seed_menus()
    idx = {m["name"].casefold(): i for i, m in enumerate(combined)}
    for row in old:
        m = fix_menu(row)
        if m:
            key = m["name"].casefold()
            if key in idx:
                # ข้อมูลที่ผู้ใช้บันทึกมีสิทธิ์เหนือค่าตัวอย่าง
                combined[idx[key]].update(m)
            else:
                idx[key] = len(combined)
                combined.append(m)
    available = {m["name"] for m in combined}
    plan = {}
    if isinstance(rawplan, dict):
        for day, names in list(rawplan.items())[:365]:
            try:
                date.fromisoformat(day)
            except (ValueError, TypeError):
                continue
            if isinstance(names, list):
                plan[day] = list(dict.fromkeys(n for n in names if isinstance(n, str) and n in available))[:5]
    return {"version": 3, "menus": combined, "plan": plan}


def alternate_group(day, start_with):
    # day parity relative to fixed calendar origin ensures continuity across separate runs
    return start_with if day.toordinal() % 2 == 0 else ("ผัดไข่" if start_with == "ยำ" else "ยำ")


def generate(start, days, rng_seed, start_with, candidates, old_plan):
    rng = random.Random(rng_seed)
    new_plan = dict(old_plan)
    history = {group: [] for group in GROUPS}
    for offset in range(days):
        day = start + timedelta(days=offset)
        fifth = alternate_group(day, start_with)
        groups = GROUPS[:4] + [fifth]
        choices = []
        for group in groups:
            pool = [m["name"] for m in candidates if m["category"] == group]
            if not pool:
                raise ValueError(f"กลุ่ม {group} ไม่มีเมนูพร้อมใช้งาน")
            recent = history[group][-3:]
            # prefer least-recent; random tie-breaking
            weights = [1 if name in recent[-1:] else 3 if name in recent else 10 for name in pool]
            picked = rng.choices(pool, weights=weights, k=1)[0]
            choices.append(picked)
            history[group].append(picked)
        new_plan[day.isoformat()] = choices
    return new_plan


def export_json(data):
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def add_menu(data, name, category, source, url, notes, status):
    name = name.strip()
    if not name:
        return "กรุณาใส่ชื่อเมนู"
    if any(m["name"].casefold() == name.casefold() for m in data["menus"]):
        return "ชื่อนี้มีอยู่ในคลังแล้ว"
    if url.strip() and not valid_url(url):
        return "ลิงก์ต้องขึ้นต้นด้วย https:// หรือ http://"
    data["menus"].append({"name": name[:120], "category": category, "source": source[:160] or "เพิ่มเอง",
                          "url": valid_url(url), "steps": notes[:10000], "status": status})
    return ""


data = store()
st.title("🍛 ข้าวแกง 40")
st.caption("V3 • วันละ 5 เมนู • ยำสลับผัดไข่ • คลังเมนู 50 อย่าง • พักต้นทุน")
st.info("ข้อมูลเก็บชั่วคราวในเซสชัน Streamlit โปรดดาวน์โหลด JSON สำรองหลังแก้ไขข้อมูลสำคัญ และก่อนปิดแอป")
with st.expander("💾 สำรอง / นำเข้าข้อมูล V1–V3"):
    st.download_button("⬇️ ดาวน์โหลดข้อมูล JSON", export_json(data),
                       file_name=f"khaokaeng40_v3_{date.today().isoformat()}.json", mime="application/json")
    incoming = st.file_uploader("นำเข้าไฟล์ JSON เก่า", type="json")
    if incoming is not None and st.button("ยืนยันนำเข้า (แทนที่ข้อมูลในแอป)"):
        try:
            if incoming.size > 3_000_000:
                raise ValueError("ไฟล์ใหญ่เกิน 3 MB")
            st.session_state.data_v3 = migrate(json.loads(incoming.getvalue().decode("utf-8")))
            st.rerun()
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as err:
            st.error(f"นำเข้าไม่สำเร็จ: {err}")

tab_run, tab_list, tab_find = st.tabs(["📅 Run เมนู", "📚 คลังเมนู", "🔎 สูตรภายนอก"])
with tab_run:
    st.subheader("วางแผนอาหาร 7–30 วัน")
    start = st.date_input("เริ่มวันที่", date.today())
    days = st.slider("วางแผนกี่วัน", 7, 30, 7)
    st.write("**5 เมนูต่อวัน:** ผัดจืด/ผัดผัก · ผัดเผ็ด · แกง · ต้มจืด · ยำ/ผัดไข่")
    start_with = st.radio("วันที่มีเลขลำดับคู่ในปฏิทินจะเป็นหมวด", ["ยำ", "ผัดไข่"], horizontal=True,
                          help="กำหนดจังหวะการสลับ โดยใช้ลำดับวันในปฏิทินเพื่อให้แผนรอบใหม่สลับต่อเนื่อง")
    seed = st.number_input("หมายเลขชุดสุ่ม", 0, 999999, 40)
    candidates = [m for m in data["menus"] if m["status"] != "พักไว้"]
    lacking = [g for g in GROUPS if not any(m["category"] == g for m in candidates)]
    if lacking:
        st.warning("ยังไม่มีเมนูพร้อมใช้งานในกลุ่ม: " + ", ".join(lacking))
    if st.button("🔄 สร้างตาราง 5 เมนู/วัน", type="primary", disabled=bool(lacking)):
        try:
            data["plan"] = generate(start, days, int(seed), start_with, candidates, data["plan"])
            st.success("สร้างตารางแล้ว เลือกเปลี่ยนเมนูในแต่ละวันได้ด้านล่าง")
        except ValueError as err:
            st.error(str(err))
    st.caption("โปรแกรมลดการซ้ำภายในหมวด แต่ไม่สามารถรับประกันว่าจะไม่ซ้ำหากมีเมนูจำกัด ตารางใหม่จะเขียนทับเฉพาะช่วงวันที่เลือก")
    by_name = {m["name"]: m for m in candidates}
    for offset in range(days):
        day = start + timedelta(days=offset)
        key = day.isoformat()
        fifth = alternate_group(day, start_with)
        groups = GROUPS[:4] + [fifth]
        existing = data["plan"].get(key, [])
        with st.expander(f"{day.strftime('%d/%m/%Y')} · {', '.join(existing) if existing else 'ยังไม่จัดเมนู'}", expanded=offset == 0):
            with st.form(f"day_{key}"):
                picked = []
                for j, group in enumerate(groups):
                    options = [m["name"] for m in candidates if m["category"] == group]
                    initial = next((x for x in existing if x in options), options[0] if options else None)
                    if options:
                        picked.append(st.selectbox(f"{j+1}. {group}", options, index=options.index(initial), key=f"{key}_{group}"))
                    else:
                        st.warning(f"ยังไม่มีอาหารในกลุ่ม {group}")
                if st.form_submit_button("💾 บันทึกเมนูวันนี้"):
                    if len(picked) == 5:
                        data["plan"][key] = picked
                        st.success("บันทึกในเซสชันแล้ว")
                        st.rerun()
                    else:
                        st.error("ต้องมีครบ 5 กลุ่มก่อนบันทึก")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["วันที่", "ผัดจืด/ผัดผัก", "ผัดเผ็ด", "แกง", "ต้มจืด", "ยำ/ผัดไข่"])
    for offset in range(days):
        day = start + timedelta(days=offset)
        row = data["plan"].get(day.isoformat(), [])
        writer.writerow([day.isoformat()] + row[:5] + [""] * (5-len(row[:5])))
    st.download_button("⬇️ ดาวน์โหลดตาราง CSV", "\ufeff" + output.getvalue(), "khaokaeng40_plan_v3.csv", "text/csv")

with tab_list:
    st.subheader("คลังเมนู — เริ่มต้น 50 รายการ")
    filter_cat = st.selectbox("เลือกกลุ่ม", ["ทั้งหมด"] + GROUPS)
    filter_status = st.selectbox("เลือกสถานะ", ["ทั้งหมด"] + STATUSES)
    keyword = st.text_input("ค้นหาชื่อเมนูในคลัง")
    shown = [(i, m) for i, m in enumerate(data["menus"]) if (filter_cat == "ทั้งหมด" or m["category"] == filter_cat)
             and (filter_status == "ทั้งหมด" or m["status"] == filter_status) and keyword.strip().casefold() in m["name"].casefold()]
    st.caption(f"พบ {len(shown)} รายการ จาก {len(data['menus'])} เมนู")
    for i, m in shown:
        with st.expander(f"{m['name']} · {m['category']} · {m['status']}"):
            st.caption(f"ที่มา: {m['source']}")
            if m["url"]:
                st.link_button("เปิดสูตรต้นฉบับ", m["url"])
            with st.form(f"edit_menu_{i}"):
                category = st.selectbox("กลุ่มอาหาร", GROUPS, index=GROUPS.index(m["category"]))
                status = st.selectbox("สถานะ", STATUSES, index=STATUSES.index(m["status"]))
                source = st.text_input("แหล่งที่มา", m["source"])
                url = st.text_input("ลิงก์สูตร", m["url"])
                steps = st.text_area("บันทึกสูตร / หมายเหตุ", m["steps"])
                if st.form_submit_button("บันทึกการแก้ไข"):
                    if url.strip() and not valid_url(url):
                        st.error("กรุณาใส่ URL แบบ https://")
                    else:
                        m.update(category=category, status=status, source=source, url=valid_url(url), steps=steps)
                        st.rerun()
    st.divider()
    st.subheader("➕ เพิ่มเมนู / ลิงก์สูตรภายนอก")
    with st.form("new_menu", clear_on_submit=True):
        name = st.text_input("ชื่อเมนู *")
        category = st.selectbox("กลุ่ม", GROUPS)
        source = st.text_input("แหล่งสูตร เช่น YouTube หรือชื่อช่อง")
        url = st.text_input("ลิงก์สูตร (ไม่บังคับ)")
        notes = st.text_area("วิธีทำหรือหมายเหตุ")
        status = st.selectbox("สถานะ", STATUSES, index=1)
        if st.form_submit_button("บันทึกเข้าคลัง"):
            err = add_menu(data, name, category, source, url, notes, status)
            if err:
                st.warning(err)
            else:
                st.success("เพิ่มเมนูแล้ว")
                st.rerun()

with tab_find:
    st.subheader("ค้นหาเมนูและสูตรจากภายนอก")
    st.caption("เปิดผลค้นหา Google/YouTube ในเบราว์เซอร์ แล้วคัดลอกชื่อเมนูและลิงก์กลับมาบันทึกในคลังเมนู ขณะนี้ยังไม่ดึงเนื้อหาสูตรอัตโนมัติ")
    q = st.text_input("คำค้น เช่น ผัดจืดทำขาย, เมนูยำ", "สูตรข้าวแกงทำขาย")
    st.link_button("🔎 ค้นผ่าน Google", "https://www.google.com/search?q=" + quote((q or "อาหารไทย") + " สูตรอาหาร"))
    st.link_button("▶️ ค้นผ่าน YouTube", "https://www.youtube.com/results?search_query=" + quote((q or "อาหารไทย") + " วิธีทำ"))
    st.info("เจอเมนูที่สนใจแล้ว ไปแท็บ ‘คลังเมนู’ → ‘เพิ่มเมนู / ลิงก์สูตรภายนอก’ เพื่อบันทึกเข้าคลังและใช้จัด Run เมนู")
    st.warning("50 เมนูเริ่มต้นเป็นเพียงไอเดียอาหาร ยังไม่ได้ตรวจสูตร ขนาดเสิร์ฟ หรือต้นทุนสำหรับขายราคาไม่เกิน 40 บาท")
