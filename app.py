import json
from pathlib import Path
from datetime import date
import streamlit as st

st.set_page_config(page_title='ข้าวแกง 40', page_icon='🍛', layout='centered')
DATA = Path('data/menus.json')
DEFAULT = [
 {'name':'ผัดพริกแกงปลาดุก','category':'ผัด','ingredients':[],'steps':'','source':'สูตรของร้าน','url':''},
 {'name':'ต้มจืดหมูสับ','category':'ต้ม','ingredients':[],'steps':'','source':'สูตรของร้าน','url':''},
 {'name':'ผัดกะเพราหมูสับ','category':'ผัด','ingredients':[],'steps':'','source':'สูตรของร้าน','url':''},
 {'name':'ยำปลาทู','category':'ยำ','ingredients':[],'steps':'','source':'สูตรของร้าน','url':''},
 {'name':'แกงกะทิไก่กับยอดมะพร้าว','category':'แกง','ingredients':[],'steps':'','source':'สูตรของร้าน','url':''},
]

def load():
    if 'menus' not in st.session_state:
        st.session_state.menus = json.loads(DATA.read_text(encoding='utf-8')) if DATA.exists() else DEFAULT
    return st.session_state.menus

def money(x): return f'{x:,.2f} บาท'

def export_data():
    return json.dumps(st.session_state.menus, ensure_ascii=False, indent=2).encode('utf-8')

menus = load()
st.title('🍛 ข้าวแกง 40')
st.caption('จัดเมนู • เก็บสูตร • คำนวณต้นทุน | ราคาขายไม่เกิน 40 บาท')
st.info('ข้อมูลที่แก้ไขอยู่ในเซสชันนี้ กรุณากด “ดาวน์โหลดสำรองข้อมูล” ก่อนปิดหรือรีสตาร์ตแอป และนำเข้าไฟล์เมื่อกลับมาใช้งาน')
with st.expander('💾 สำรอง / นำเข้าข้อมูล'):
    st.download_button('ดาวน์โหลดสำรองข้อมูล JSON', export_data(), file_name='khaokaeng40_backup.json', mime='application/json')
    uploaded = st.file_uploader('นำเข้าไฟล์สำรอง JSON', type=['json'])
    if uploaded and st.button('ยืนยันนำเข้าข้อมูล'):
        try:
            obj = json.load(uploaded)
            if not isinstance(obj,list) or any(not isinstance(x,dict) or 'name' not in x for x in obj):
                raise ValueError('รูปแบบไฟล์ไม่ถูกต้อง')
            st.session_state.menus = obj
            st.success('นำเข้าข้อมูลแล้ว')
            st.rerun()
        except (ValueError, json.JSONDecodeError) as e: st.error(str(e))

tab1, tab2, tab3 = st.tabs(['📅 เมนูวันนี้','📖 คลังสูตร','💰 ต้นทุน'])
with tab1:
    st.subheader(f'วางแผนเมนูวันที่ {date.today().strftime("%d/%m/%Y")}')
    choices = st.multiselect('เลือก 3–5 เมนู', [m['name'] for m in menus], default=[m['name'] for m in menus[:min(5,len(menus))]])
    if not 3 <= len(choices) <= 5: st.warning('แนะนำให้เลือก 3–5 เมนูต่อวัน')
    for i, name in enumerate(choices,1): st.write(f'{i}. {name}')
    st.caption('เวอร์ชันนี้เป็นแผนเมนูชั่วคราว ยังไม่บันทึกตารางรายวันแบบถาวร')
with tab2:
    names = [m['name'] for m in menus]
    choice = st.selectbox('เลือกสูตร',names) if names else None
    if choice:
        m = next(x for x in menus if x['name']==choice)
        st.write('ประเภท:',m.get('category','-'))
        st.write('ที่มา:',m.get('source','-'))
        if m.get('url'): st.link_button('เปิดแหล่งสูตร',m['url'])
        with st.form('edit_recipe'):
            category=st.selectbox('ประเภท', ['ผัด','ต้ม','แกง','ยำ','ทอด','อื่น ๆ'],index=['ผัด','ต้ม','แกง','ยำ','ทอด','อื่น ๆ'].index(m.get('category','อื่น ๆ')) if m.get('category') in ['ผัด','ต้ม','แกง','ยำ','ทอด','อื่น ๆ'] else 5)
            steps=st.text_area('ขั้นตอนทำอาหาร',value=m.get('steps',''))
            source=st.text_input('แหล่งสูตร / ชื่อช่อง',value=m.get('source',''))
            url=st.text_input('ลิงก์สูตร (ถ้ามี)',value=m.get('url',''))
            if st.form_submit_button('บันทึกสูตร'):
                m.update(category=category,steps=steps,source=source,url=url)
                st.success('บันทึกในเซสชันแล้ว อย่าลืมสำรองข้อมูล')
        st.markdown('**วัตถุดิบและต้นทุนสำหรับสูตรนี้**')
        for idx, ing in enumerate(m.get('ingredients',[])):
            st.write(f"• {ing['name']}: {ing['quantity']} {ing['unit']} × {money(ing['unit_cost'])}/{ing['unit']}")
        with st.form('add_ingredient',clear_on_submit=True):
            item=st.text_input('ชื่อวัตถุดิบ')
            c1,c2,c3=st.columns(3)
            with c1: qty=st.number_input('ปริมาณที่ใช้',min_value=0.01,value=1.0,step=0.5)
            with c2: unit=st.selectbox('หน่วย',['กรัม','กก.','ฟอง','มล.','ลิตร','ชิ้น','บาท'])
            with c3: unit_cost=st.number_input('ราคา/หน่วย (บาท)',min_value=0.0,value=0.0,step=1.0)
            if st.form_submit_button('เพิ่มวัตถุดิบ'):
                if item.strip():
                    m.setdefault('ingredients',[]).append({'name':item.strip(),'quantity':qty,'unit':unit,'unit_cost':unit_cost})
                    st.rerun()
                else: st.error('กรุณาระบุชื่อวัตถุดิบ')
        if m.get('ingredients'):
            if st.button('ล้างรายการวัตถุดิบของสูตรนี้'):
                m['ingredients']=[];st.rerun()
    st.divider()
    with st.form('new_recipe'):
        st.markdown('**เพิ่มเมนูใหม่จากร้านหรือแหล่งภายนอก**')
        newname=st.text_input('ชื่อเมนูใหม่')
        newsource=st.text_input('แหล่งที่มา',value='สูตรจากภายนอก')
        newurl=st.text_input('URL สูตร เช่น YouTube / เว็บไซต์')
        if st.form_submit_button('เพิ่มเมนู'):
            if not newname.strip(): st.error('กรุณากรอกชื่อเมนู')
            elif newname.strip() in names: st.error('ชื่อเมนูนี้มีแล้ว')
            else:
                menus.append({'name':newname.strip(),'category':'อื่น ๆ','ingredients':[],'steps':'','source':newsource,'url':newurl})
                st.rerun()
    st.link_button('ค้นหาไอเดียสูตรอาหารบน Google','https://www.google.com/search?q=สูตรอาหารไทย+ข้าวแกง')
with tab3:
    if not menus: st.warning('กรุณาเพิ่มเมนูก่อน')
    else:
        selected=st.selectbox('เมนูที่ต้องการคำนวณ',[m['name'] for m in menus],key='costmenu')
        m=next(x for x in menus if x['name']==selected)
        ingredients=m.get('ingredients',[])
        ingredient_total=sum(float(x['quantity'])*float(x['unit_cost']) for x in ingredients)
        st.write('ต้นทุนวัตถุดิบทั้งสูตร:',money(ingredient_total))
        portions=st.number_input('สูตรนี้แบ่งขายได้กี่ถุง/ส่วน',min_value=1,value=20,step=1)
        packaging=st.number_input('ค่าถุง/บรรจุภัณฑ์ต่อถุง (บาท)',min_value=0.0,value=0.0,step=0.5)
        rice=st.number_input('ต้นทุนข้าวต่อจาน (บาท)',min_value=0.0,value=0.0,step=0.5)
        platepack=st.number_input('ต้นทุนกล่อง/ภาชนะต่อจาน (บาท)',min_value=0.0,value=0.0,step=0.5)
        selling=st.number_input('ราคาขายต่อหน่วย (ไม่เกิน 40 บาท)',min_value=1.0,max_value=40.0,value=40.0,step=1.0)
        per=ingredient_total/portions
        a=per+packaging;b=per+rice+platepack
        st.metric('ต้นทุนต่อถุง',money(a),delta=f'ส่วนต่าง {money(selling-a)}',delta_color='normal')
        st.metric('ต้นทุนต่อจานราดข้าว',money(b),delta=f'ส่วนต่าง {money(selling-b)}',delta_color='normal')
        if not ingredients: st.warning('ยังไม่มีข้อมูลวัตถุดิบ ผลลัพธ์จึงยังไม่ใช่ต้นทุนจริง')
        st.caption('ส่วนต่างยังไม่ใช่กำไรสุทธิ: ไม่รวมค่าแก๊ส ค่าแรง ค่าเช่า อาหารเหลือ และค่าใช้จ่ายอื่นที่ไม่ได้บันทึก')
