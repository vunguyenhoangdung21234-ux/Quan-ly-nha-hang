import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import datetime
import pandas as pd

# ====================== CẤU HÌNH & GIAO DIỆN CSS ======================
st.set_page_config(page_title="Hệ Thống Nhà Hàng Pro v6.0", layout="wide", page_icon="🥘")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .table-status-card {
        border-radius: 15px; padding: 20px; text-align: center; color: white;
        font-weight: bold; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin-bottom: 10px; transition: transform 0.2s;
    }
    .table-status-card:hover { transform: scale(1.02); }
    .status-empty { background: linear-gradient(135deg, #28a745, #218838); }
    .status-occupied { background: linear-gradient(135deg, #dc3545, #c82333); }
    .cate-tag {
        background-color: #007bff; color: white; padding: 3px 10px;
        border-radius: 20px; font-size: 11px;
    }
    </style>
    """, unsafe_allow_html=True)

# ====================== KẾT NỐI GOOGLE SHEETS ======================
conn = st.connection("gsheets", type=GSheetsConnection)

def load_gsheet_data():
    # Đọc dữ liệu từ Sheet của bạn
    return conn.read(ttl=0)

# ====================== HÀM XỬ LÝ DỮ LIỆU ======================

def aggregate_orders(orders):
    if not orders: return []
    agg = {}
    for o in orders:
        code = o["code"]
        if code in agg:
            agg[code]["quantity"] += o["quantity"]
            # Gộp ghi chú nếu có
            if o.get("note"):
                agg[code]["note"] = agg[code].get("note", "") + f"; {o['note']}"
        else:
            agg[code] = o.copy()
    return list(agg.values())

def init_data():
    # Lấy menu từ Sheets thay vì gõ tay
    try:
        df_menu = load_gsheet_data()
        # Chuyển DataFrame thành dict menu giống bản cũ để không hỏng logic bên dưới
        menu_dict = {}
        for _, row in df_menu.iterrows():
            menu_dict[str(row['Mã món'])] = {
                "name": row['Tên món'],
                "category": row['Phân loại'],
                "price": int(row['Giá bán (đ)'])
            }
        st.session_state.menu = menu_dict
    except:
        if "menu" not in st.session_state:
            st.warning("Không thể kết nối Google Sheets. Đang dùng dữ liệu tạm thời.")
            st.session_state.menu = {"CO01": {"name": "Cơm niêu", "category": "Cơm", "price": 30000}}

    if "tables" not in st.session_state:
        st.session_state.tables = {f"Bàn {i}": [] for i in range(1, 13)} # Mở rộng lên 12 bàn

    if "order_id" not in st.session_state:
        st.session_state.order_id = 1
    
    if "revenue_history" not in st.session_state:
        st.session_state.revenue_history = []

init_data()

# ====================== THANH ĐIỀU HƯỚNG ======================

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3448/3448609.png", width=100)
    st.title("QUẢN LÝ NHÀ HÀNG")
    st.divider()
    page = st.radio("CHỨC NĂNG", [
        "🏠 Màn Hình Tổng Quát",
        "🛒 Quản Lý Đặt Món",
        "📋 Danh Mục Thực Đơn",
        "📊 Báo Cáo Doanh Thu",
        "⚙️ Cài Đặt Hệ Thống"
    ])
    if st.button("🔄 Làm mới dữ liệu từ Sheets"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption(f"📅 Hôm nay: {datetime.now().strftime('%d/%m/%Y')}")

# =============================================================
# ================ 1. 🏠 MÀN HÌNH TỔNG QUÁT ===================
# =============================================================

if page == "🏠 Màn Hình Tổng Quát":
    st.title("🏠 TRẠNG THÁI TOÀN BỘ BÀN ĂN")
    
    total_active = sum(1 for t in st.session_state.tables.values() if len(t) > 0)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Bàn Đang Dùng", f"{total_active} / 12")
    col2.metric("Bàn Trống", f"{12 - total_active}")
    
    st.divider()

    # Mở rộng grid bàn
    for row in range(0, 12, 4):
        cols = st.columns(4)
        for i in range(4):
            table_idx = row + i + 1
            if table_idx > 12: break
            t_name = f"Bàn {table_idx}"
            orders = st.session_state.tables[t_name]
            is_busy = len(orders) > 0
            
            with cols[i]:
                status_class = "status-occupied" if is_busy else "status-empty"
                st.markdown(f"""
                    <div class="table-status-card {status_class}">
                        <div style='font-size: 32px;'>{table_idx}</div>
                        <div style='font-size: 14px;'>{t_name}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                if is_busy:
                    with st.expander("Món đang dùng"):
                        agg_list = aggregate_orders(orders)
                        total_tmp = 0
                        for o in agg_list:
                            item = st.session_state.menu[o["code"]]
                            st.write(f"• **{o['quantity']}x** {item['name']}")
                            total_tmp += item['price'] * o['quantity']
                        st.markdown(f"**Tạm tính: {total_tmp:,}đ**")

# =============================================================
# ================ 2. 🛒 QUẢN LÝ ĐẶT MÓN =======================
# =============================================================

elif page == "🛒 Quản Lý Đặt Món":
    st.title("🛒 CHI TIẾT PHỤC VỤ TẠI BÀN")
    
    table_choice = st.selectbox("🎯 Chọn bàn thao tác", list(st.session_state.tables.keys()))
    orders = st.session_state.tables[table_choice]

    c1, c2 = st.columns([2, 1])

    with c1:
        st.subheader(f"Danh sách Order của {table_choice}")
        if not orders:
            st.info("Bàn này hiện đang trống.")
        else:
            agg_orders = aggregate_orders(orders)
            total_money = 0
            
            h1, h2, h3, h4 = st.columns([3, 1, 1.5, 1.5])
            h1.write("**Món ăn**")
            h2.write("**SL**")
            h3.write("**Thành tiền**")
            h4.write("**Thao tác**")
            
            for idx, o in enumerate(agg_orders):
                item = st.session_state.menu[o["code"]]
                line_total = item["price"] * o["quantity"]
                total_money += line_total
                
                r1, r2, r3, r4 = st.columns([3, 1, 1.5, 1.5])
                r1.write(f"**{item['name']}**")
                r2.write(o["quantity"])
                r3.write(f"{line_total:,}đ")
                
                stt_label = "✅ Đã lên" if o["status"] == "Đã lên" else "⏳ Chưa lên"
                if r4.button(stt_label, key=f"stt_{table_choice}_{o['code']}"):
                    new_stt = "Đã lên" if o["status"] == "Chưa lên" else "Chưa lên"
                    for origin_item in orders:
                        if origin_item["code"] == o["code"]:
                            origin_item["status"] = new_stt
                    st.rerun()

            st.markdown(f"### 💵 TỔNG THANH TOÁN: {total_money:,} VNĐ")
            
            # --- THANH TOÁN & ĐỒNG BỘ SHEETS ---
            if st.button("💳 XÁC NHẬN THANH TOÁN & ĐẨY LÊN SHEETS", type="primary", use_container_width=True):
                # 1. Đọc dữ liệu Sheet hiện tại
                df_gsheet = load_gsheet_data()
                
                # 2. Cập nhật Số lượng & Doanh thu
                for o in agg_orders:
                    it = st.session_state.menu[o["code"]]
                    món_tên = it["name"]
                    tiền_món = it["price"] * o["quantity"]
                    
                    # Tìm dòng trên Sheet dựa vào Tên món
                    mask = df_gsheet['Tên món'] == món_tên
                    if mask.any():
                        idx = df_gsheet.index[mask][0]
                        # Chuyển đổi tránh lỗi NaN
                        curr_qty = pd.to_numeric(df_gsheet.at[idx, 'Số lượng'], errors='coerce') or 0
                        curr_rev = pd.to_numeric(df_gsheet.at[idx, 'Doanh thu'], errors='coerce') or 0
                        
                        df_gsheet.at[idx, 'Số lượng'] = curr_qty + o["quantity"]
                        df_gsheet.at[idx, 'Doanh thu'] = curr_rev + tiền_món
                    
                    # Lưu vào lịch sử cục bộ của App
                    st.session_state.revenue_history.append({
                        "Thời gian": datetime.now().strftime("%H:%M:%S"),
                        "Món": món_tên,
                        "Phân loại": it["category"],
                        "Số lượng": o["quantity"],
                        "Tiền": tiền_món
                    })
                
                # 3. Đẩy ngược lại Sheets
                conn.update(data=df_gsheet)
                st.session_state.tables[table_choice] = []
                st.success("✅ Thanh toán thành công & Đã đồng bộ lên Google Sheets!")
                st.rerun()

    with c2:
        st.subheader("Gọi món mới")
        with st.form("form_order"):
            dish_code = st.selectbox("Món ăn", list(st.session_state.menu.keys()), 
                                    format_func=lambda x: f"{st.session_state.menu[x]['name']} - {st.session_state.menu[x]['price']:,}đ")
            qty = st.number_input("Số lượng", min_value=1, value=1)
            note = st.text_input("Ghi chú (VD: Không hành, cay...)")
            if st.form_submit_button("➕ Thêm vào bàn", use_container_width=True):
                st.session_state.tables[table_choice].append({
                    "id": st.session_state.order_id,
                    "code": dish_code,
                    "quantity": qty,
                    "status": "Chưa lên",
                    "note": note,
                    "time": datetime.now().strftime("%H:%M")
                })
                st.session_state.order_id += 1
                st.rerun()

# =============================================================
# ================ 3. 📋 DANH MỤC THỰC ĐƠN =====================
# =============================================================

elif page == "📋 Danh Mục Thực Đơn":
    st.title("📋 QUẢN LÝ THỰC ĐƠN (ĐỒNG BỘ SHEETS)")
    
    # Dùng data_editor để sửa như Excel
    df_menu_edit = load_gsheet_data()
    edited_df = st.data_editor(df_menu_edit, num_rows="dynamic", use_container_width=True, key="menu_editor")
    
    if st.button("💾 Lưu tất cả thay đổi lên Google Sheets"):
        conn.update(data=edited_df)
        st.success("Đã cập nhật thực đơn lên Sheets!")
        st.cache_data.clear()
        st.rerun()

# =============================================================
# ================ 4. 📊 BÁO CÁO DOANH THU =====================
# =============================================================

elif page == "📊 Báo Cáo Doanh Thu":
    st.title("📊 PHÂN TÍCH DOANH THU")
    # Đọc doanh thu tổng từ Sheet để báo cáo chính xác nhất
    df_total = load_gsheet_data()
    
    m1, m2, m3 = st.columns(3)
    total_rev = pd.to_numeric(df_total['Doanh thu'], errors='coerce').sum()
    m1.metric("TỔNG DOANH THU (SHEETS)", f"{total_rev:,}đ")
    m2.metric("SỐ MÓN TRONG MENU", len(df_total))
    
    st.divider()
    st.subheader("Biểu đồ doanh thu theo món")
    st.bar_chart(df_total.set_index("Tên món")["Doanh thu"])
    
    st.subheader("Bảng dữ liệu chi tiết từ Sheets")
    st.dataframe(df_total, use_container_width=True)

# =============================================================
# ================ 5. ⚙️ CÀI ĐẶT HỆ THỐNG =======================
# =============================================================

elif page == "⚙️ Cài Đặt Hệ Thống":
    st.title("⚙️ CÀI ĐẶT")
    if st.button("🚨 RESET TOÀN BỘ DỮ LIỆU TẠI BÀN", type="primary"):
        st.session_state.tables = {f"Bàn {i}": [] for i in range(1, 13)}
        st.rerun()
