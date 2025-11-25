import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image

# Page configuration
st.set_page_config(
    page_title="Ruchitara Foods - Inventory Management",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2E7D32;
        font-weight: bold;
        text-align: center;
        padding: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .category-badge {
        background-color: #4CAF50;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.9rem;
    }
    .low-stock {
        background-color: #ff5252;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
    }
    .good-stock {
        background-color: #4CAF50;
        color: white;
        padding: 0.2rem 0.5rem;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Database initialization
def init_db():
    """Initialize SQLite database with products table"""
    conn = sqlite3.connect('ruchitara_inventory.db')
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            weight TEXT,
            price REAL NOT NULL,
            quantity INTEGER DEFAULT 0,
            category TEXT NOT NULL,
            image_url TEXT,
            pre_order_only INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# CRUD Operations
def add_product(sku_code, name, description, weight, price, quantity, category, image_url="", pre_order_only=0):
    """Add a new product to the database"""
    try:
        conn = sqlite3.connect('ruchitara_inventory.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO products (sku_code, name, description, weight, price, quantity, category, image_url, pre_order_only)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (sku_code, name, description, weight, price, quantity, category, image_url, pre_order_only))
        conn.commit()
        conn.close()
        return True, "Product added successfully!"
    except sqlite3.IntegrityError:
        return False, "Product with this SKU code already exists!"
    except Exception as e:
        return False, f"Error: {str(e)}"

def get_all_products():
    """Retrieve all products from database"""
    conn = sqlite3.connect('ruchitara_inventory.db')
    df = pd.read_sql_query("SELECT * FROM products ORDER BY category, name", conn)
    conn.close()
    return df

def get_product_by_sku(sku_code):
    """Get a specific product by SKU code"""
    conn = sqlite3.connect('ruchitara_inventory.db')
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE sku_code = ?", (sku_code,))
    product = c.fetchone()
    conn.close()
    return product

def update_product(sku_code, name, description, weight, price, quantity, category, image_url="", pre_order_only=0):
    """Update existing product"""
    try:
        conn = sqlite3.connect('ruchitara_inventory.db')
        c = conn.cursor()
        c.execute('''
            UPDATE products 
            SET name=?, description=?, weight=?, price=?, quantity=?, category=?, image_url=?, pre_order_only=?, last_updated=?
            WHERE sku_code=?
        ''', (name, description, weight, price, quantity, category, image_url, pre_order_only, datetime.now(), sku_code))
        conn.commit()
        conn.close()
        return True, "Product updated successfully!"
    except Exception as e:
        return False, f"Error: {str(e)}"

def delete_product(sku_code):
    """Delete a product from database"""
    try:
        conn = sqlite3.connect('ruchitara_inventory.db')
        c = conn.cursor()
        c.execute("DELETE FROM products WHERE sku_code = ?", (sku_code,))
        conn.commit()
        conn.close()
        return True, "Product deleted successfully!"
    except Exception as e:
        return False, f"Error: {str(e)}"

def update_stock(sku_code, quantity_change):
    """Update stock quantity (add or subtract)"""
    try:
        conn = sqlite3.connect('ruchitara_inventory.db')
        c = conn.cursor()
        c.execute('''
            UPDATE products 
            SET quantity = quantity + ?, last_updated = ?
            WHERE sku_code = ?
        ''', (quantity_change, datetime.now(), sku_code))
        conn.commit()
        conn.close()
        return True, "Stock updated successfully!"
    except Exception as e:
        return False, f"Error: {str(e)}"

def get_categories():
    """Get all unique categories"""
    conn = sqlite3.connect('ruchitara_inventory.db')
    c = conn.cursor()
    c.execute("SELECT DISTINCT category FROM products ORDER BY category")
    categories = [row[0] for row in c.fetchall()]
    conn.close()
    return categories

def get_stats():
    """Get inventory statistics"""
    conn = sqlite3.connect('ruchitara_inventory.db')
    c = conn.cursor()
    
    # Total products
    c.execute("SELECT COUNT(*) FROM products")
    total_products = c.fetchone()[0]
    
    # Low stock count (quantity < 10)
    c.execute("SELECT COUNT(*) FROM products WHERE quantity < 10")
    low_stock = c.fetchone()[0]
    
    # Total inventory value
    c.execute("SELECT SUM(price * quantity) FROM products")
    total_value = c.fetchone()[0] or 0
    
    # Out of stock
    c.execute("SELECT COUNT(*) FROM products WHERE quantity = 0")
    out_of_stock = c.fetchone()[0]
    
    conn.close()
    return {
        'total_products': total_products,
        'low_stock': low_stock,
        'total_value': total_value,
        'out_of_stock': out_of_stock
    }

def load_initial_products():
    """Load initial product data from RUCHITARA catalog"""
    
    # Check if products already exist
    df = get_all_products()
    if len(df) > 0:
        return
    
    # BATTERS - Regular products
    batters = [
        ("210610", "Dosa Batter", "Traditional dosa batter for crispy dosas", "500g", 50, 0, "BATTERS", "", 0),
        ("210611", "Idli Batter", "Soft and fluffy idli batter", "500g", 50, 0, "BATTERS", "", 0),
        ("210612", "Wada Batter", "Perfect wada batter (Pre-order only)", "1kg", 125, 0, "BATTERS", "", 1),
        ("210613", "Green Gram Batter", "Nutritious green gram batter (Pre-order only)", "500g", 50, 0, "BATTERS", "", 1),
        ("210614", "Finger Millet Dosa Batter (Ragi Dosa)", "Healthy ragi dosa batter", "500g", 55, 0, "BATTERS", "", 0),
        ("210615", "Finger Millet Idli Batter (Ragi Idli)", "Healthy ragi idli batter", "500g", 55, 0, "BATTERS", "", 0),
        ("210616", "Foxtail Millet Dosa Batter (Korra Dosa)", "Nutritious foxtail millet dosa", "500g", 55, 0, "BATTERS", "", 0),
        ("210617", "Foxtail Millet Idli Batter (Korra Idli)", "Nutritious foxtail millet idli", "500g", 55, 0, "BATTERS", "", 0),
        ("210618", "Little Millet Dosa Batter (Samala Dosa)", "Little millet dosa batter", "500g", 55, 0, "BATTERS", "", 0),
        ("210619", "Little Millet Idli Batter (Samala Idli)", "Little millet idli batter", "500g", 55, 0, "BATTERS", "", 0),
        ("210620", "Browntop Millet Dosa Batter (Anndukorrala Dosa)", "Browntop millet dosa", "500g", 55, 0, "BATTERS", "", 0),
        ("210621", "Browntop Millet Idli Batter (Anndukorrala Idli)", "Browntop millet idli", "500g", 55, 0, "BATTERS", "", 0),
        ("210622", "Pearl Millet Dosa Batter (Sajjala Dosa)", "Pearl millet dosa batter", "500g", 55, 0, "BATTERS", "", 0),
        ("210623", "White Sorghum Dosa Batter (Jonna Dosa)", "White sorghum dosa batter", "500g", 55, 0, "BATTERS", "", 0),
    ]
    
    # SPICED POWDERS - Products with variants
    spiced_powders = [
        ("91010-100", "Flaxseed Spiced Powder", "Nutritious flaxseed spiced powder", "100g", 70, 0, "SPICED POWDERS", "", 0),
        ("91010-250", "Flaxseed Spiced Powder", "Nutritious flaxseed spiced powder", "250g", 175, 0, "SPICED POWDERS", "", 0),
        ("91011-100", "Peanuts Spiced Powder", "Crunchy peanuts spiced powder", "100g", 60, 0, "SPICED POWDERS", "", 0),
        ("91011-250", "Peanuts Spiced Powder", "Crunchy peanuts spiced powder", "250g", 150, 0, "SPICED POWDERS", "", 0),
        ("91012-100", "Roasted Gram Spiced Powder", "Roasted gram spiced powder", "100g", 50, 0, "SPICED POWDERS", "", 0),
        ("91012-250", "Roasted Gram Spiced Powder", "Roasted gram spiced powder", "250g", 125, 0, "SPICED POWDERS", "", 0),
        ("91013-100", "All Pulses Spiced Powder", "Mixed pulses spiced powder", "100g", 60, 0, "SPICED POWDERS", "", 0),
        ("91013-250", "All Pulses Spiced Powder", "Mixed pulses spiced powder", "250g", 150, 0, "SPICED POWDERS", "", 0),
        ("91014-100", "Curry Leaves Spiced Powder", "Aromatic curry leaves powder", "100g", 50, 0, "SPICED POWDERS", "", 0),
        ("91014-250", "Curry Leaves Spiced Powder", "Aromatic curry leaves powder", "250g", 125, 0, "SPICED POWDERS", "", 0),
        ("91015-100", "Garlic Spiced Powder", "Flavorful garlic spiced powder", "100g", 70, 0, "SPICED POWDERS", "", 0),
        ("91015-250", "Garlic Spiced Powder", "Flavorful garlic spiced powder", "250g", 175, 0, "SPICED POWDERS", "", 0),
        ("91016-100", "Bitter Gourd & Garlic Spiced Powder", "Healthy bitter gourd & garlic powder (Coming Soon)", "100g", 80, 0, "SPICED POWDERS", "", 0),
        ("91016-250", "Bitter Gourd & Garlic Spiced Powder", "Healthy bitter gourd & garlic powder (Coming Soon)", "250g", 200, 0, "SPICED POWDERS", "", 0),
    ]
    
    # Insert all products
    for product in batters + spiced_powders:
        add_product(*product)

# Main Application
def main():
    # Initialize database
    init_db()
    
    # Load initial products
    load_initial_products()
    
    # Header
    st.markdown('<p class="main-header">🌾 RUCHITARA FOODS - Inventory Management</p>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Sidebar navigation
    with st.sidebar:
        st.image("https://via.placeholder.com/150x80/4CAF50/FFFFFF?text=RUCHITARA", use_column_width=True)
        st.markdown("## Navigation")
        menu = st.radio(
            "Select Option",
            ["📊 Dashboard", "📦 View Products", "➕ Add Product", "✏️ Update Product", 
             "🗑️ Delete Product", "📈 Stock Management", "📥 Bulk Upload"]
        )
        
        st.markdown("---")
        st.markdown("### Contact Info")
        st.markdown("📞 8500 834 534")
        st.markdown("📞 94038 93333")
        st.markdown("📧 info@ruchitara.in")
        st.markdown("🏢 b2b@ruchitara.in")
    
    # Dashboard
    if menu == "📊 Dashboard":
        st.header("Dashboard Overview")
        
        # Get statistics
        stats = get_stats()
        
        # Display metrics in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Products", stats['total_products'], help="Total number of products in inventory")
        
        with col2:
            st.metric("Low Stock Items", stats['low_stock'], delta=f"-{stats['low_stock']}", 
                     delta_color="inverse", help="Products with quantity less than 10")
        
        with col3:
            st.metric("Out of Stock", stats['out_of_stock'], delta=f"-{stats['out_of_stock']}", 
                     delta_color="inverse", help="Products with zero quantity")
        
        with col4:
            st.metric("Total Inventory Value", f"₹{stats['total_value']:,.2f}", help="Total value of all products")
        
        st.markdown("---")
        
        # Low stock alerts
        st.subheader("⚠️ Low Stock Alerts")
        df = get_all_products()
        low_stock_df = df[df['quantity'] < 10].sort_values('quantity')
        
        if len(low_stock_df) > 0:
            st.dataframe(
                low_stock_df[['sku_code', 'name', 'weight', 'quantity', 'category']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("✅ All products have adequate stock!")
        
        # Category-wise summary
        st.markdown("---")
        st.subheader("📊 Category-wise Summary")
        
        category_summary = df.groupby('category').agg({
            'id': 'count',
            'quantity': 'sum',
            'price': lambda x: (x * df.loc[x.index, 'quantity']).sum()
        }).reset_index()
        category_summary.columns = ['Category', 'Product Count', 'Total Quantity', 'Total Value']
        category_summary['Total Value'] = category_summary['Total Value'].apply(lambda x: f"₹{x:,.2f}")
        
        st.dataframe(category_summary, use_container_width=True, hide_index=True)
    
    # View Products
    elif menu == "📦 View Products":
        st.header("Product Catalog")
        
        df = get_all_products()
        
        if len(df) == 0:
            st.warning("No products found in inventory!")
            return
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            categories = ['All'] + get_categories()
            selected_category = st.selectbox("Filter by Category", categories)
        
        with col2:
            search_term = st.text_input("🔍 Search Products", placeholder="Enter product name or SKU...")
        
        with col3:
            sort_by = st.selectbox("Sort by", ["Name", "Price (Low to High)", "Price (High to Low)", 
                                                 "Quantity (Low to High)", "Quantity (High to Low)"])
        
        # Apply filters
        if selected_category != 'All':
            df = df[df['category'] == selected_category]
        
        if search_term:
            df = df[df['name'].str.contains(search_term, case=False) | 
                   df['sku_code'].str.contains(search_term, case=False)]
        
        # Apply sorting
        if sort_by == "Name":
            df = df.sort_values('name')
        elif sort_by == "Price (Low to High)":
            df = df.sort_values('price')
        elif sort_by == "Price (High to Low)":
            df = df.sort_values('price', ascending=False)
        elif sort_by == "Quantity (Low to High)":
            df = df.sort_values('quantity')
        elif sort_by == "Quantity (High to Low)":
            df = df.sort_values('quantity', ascending=False)
        
        st.markdown(f"**Showing {len(df)} products**")
        
        # Display products in cards
        for idx, row in df.iterrows():
            with st.expander(f"**{row['name']}** - {row['weight']} | SKU: {row['sku_code']}"):
                col1, col2 = st.columns([2, 3])
                
                with col1:
                    st.markdown(f"**Category:** {row['category']}")
                    st.markdown(f"**Price:** ₹{row['price']}")
                    st.markdown(f"**Weight:** {row['weight']}")
                    
                    # Stock status with color
                    if row['quantity'] == 0:
                        st.markdown(f"**Stock:** <span class='low-stock'>OUT OF STOCK</span>", unsafe_allow_html=True)
                    elif row['quantity'] < 10:
                        st.markdown(f"**Stock:** <span class='low-stock'>{row['quantity']} units (Low Stock)</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"**Stock:** <span class='good-stock'>{row['quantity']} units</span>", unsafe_allow_html=True)
                    
                    if row['pre_order_only']:
                        st.warning("⏰ Pre-order Only")
                
                with col2:
                    st.markdown(f"**Description:** {row['description']}")
                    st.markdown(f"**SKU Code:** {row['sku_code']}")
                    st.markdown(f"**Last Updated:** {row['last_updated']}")
        
        # Export to CSV
        st.markdown("---")
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"ruchitara_products_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    # Add Product
    elif menu == "➕ Add Product":
        st.header("Add New Product")
        
        with st.form("add_product_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                sku_code = st.text_input("SKU Code*", placeholder="e.g., 210624")
                name = st.text_input("Product Name*", placeholder="e.g., Dosa Batter")
                weight = st.text_input("Weight*", placeholder="e.g., 500g")
                price = st.number_input("Price (₹)*", min_value=0.0, step=0.5)
            
            with col2:
                category = st.selectbox("Category*", ["BATTERS", "SPICED POWDERS", "OTHER"])
                quantity = st.number_input("Initial Quantity", min_value=0, step=1, value=0)
                pre_order_only = st.checkbox("Pre-order Only")
            
            description = st.text_area("Description", placeholder="Enter product description...")
            
            # Image upload (optional)
            st.markdown("**Product Image (Optional)**")
            uploaded_file = st.file_uploader("Choose an image", type=['png', 'jpg', 'jpeg'])
            image_url = ""
            
            if uploaded_file is not None:
                # Convert image to base64
                image = Image.open(uploaded_file)
                buffered = BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                image_url = f"data:image/png;base64,{img_str}"
                st.image(image, caption="Preview", width=200)
            
            submitted = st.form_submit_button("Add Product", use_container_width=True)
            
            if submitted:
                if not sku_code or not name or not weight or price <= 0:
                    st.error("Please fill in all required fields marked with *")
                else:
                    success, message = add_product(
                        sku_code, name, description, weight, price, quantity, 
                        category, image_url, 1 if pre_order_only else 0
                    )
                    if success:
                        st.success(message)
                        st.balloons()
                    else:
                        st.error(message)
    
    # Update Product
    elif menu == "✏️ Update Product":
        st.header("Update Product")
        
        df = get_all_products()
        
        if len(df) == 0:
            st.warning("No products available to update!")
            return
        
        # Select product to update
        product_options = [f"{row['sku_code']} - {row['name']}" for _, row in df.iterrows()]
        selected_product = st.selectbox("Select Product to Update", product_options)
        
        if selected_product:
            sku_code = selected_product.split(' - ')[0]
            product = get_product_by_sku(sku_code)
            
            if product:
                with st.form("update_product_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.text_input("SKU Code", value=product[1], disabled=True)
                        name = st.text_input("Product Name*", value=product[2])
                        weight = st.text_input("Weight*", value=product[4])
                        price = st.number_input("Price (₹)*", value=float(product[5]), min_value=0.0, step=0.5)
                    
                    with col2:
                        category = st.selectbox("Category*", ["BATTERS", "SPICED POWDERS", "OTHER"], 
                                                index=["BATTERS", "SPICED POWDERS", "OTHER"].index(product[7]) if product[7] in ["BATTERS", "SPICED POWDERS", "OTHER"] else 0)
                        quantity = st.number_input("Quantity", value=int(product[6]), min_value=0, step=1)
                        pre_order_only = st.checkbox("Pre-order Only", value=bool(product[9]))
                    
                    description = st.text_area("Description", value=product[3] if product[3] else "")
                    
                    # Image upload (optional)
                    st.markdown("**Update Product Image (Optional)**")
                    uploaded_file = st.file_uploader("Choose an image", type=['png', 'jpg', 'jpeg'])
                    image_url = product[8] if product[8] else ""
                    
                    if uploaded_file is not None:
                        image = Image.open(uploaded_file)
                        buffered = BytesIO()
                        image.save(buffered, format="PNG")
                        img_str = base64.b64encode(buffered.getvalue()).decode()
                        image_url = f"data:image/png;base64,{img_str}"
                        st.image(image, caption="New Preview", width=200)
                    
                    submitted = st.form_submit_button("Update Product", use_container_width=True)
                    
                    if submitted:
                        if not name or not weight or price <= 0:
                            st.error("Please fill in all required fields marked with *")
                        else:
                            success, message = update_product(
                                sku_code, name, description, weight, price, quantity, 
                                category, image_url, 1 if pre_order_only else 0
                            )
                            if success:
                                st.success(message)
                                st.balloons()
                            else:
                                st.error(message)
    
    # Delete Product
    elif menu == "🗑️ Delete Product":
        st.header("Delete Product")
        
        df = get_all_products()
        
        if len(df) == 0:
            st.warning("No products available to delete!")
            return
        
        st.warning("⚠️ This action cannot be undone!")
        
        # Select product to delete
        product_options = [f"{row['sku_code']} - {row['name']}" for _, row in df.iterrows()]
        selected_product = st.selectbox("Select Product to Delete", product_options)
        
        if selected_product:
            sku_code = selected_product.split(' - ')[0]
            product = get_product_by_sku(sku_code)
            
            if product:
                st.markdown("### Product Details")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**SKU Code:** {product[1]}")
                    st.markdown(f"**Name:** {product[2]}")
                    st.markdown(f"**Category:** {product[7]}")
                
                with col2:
                    st.markdown(f"**Weight:** {product[4]}")
                    st.markdown(f"**Price:** ₹{product[5]}")
                    st.markdown(f"**Quantity:** {product[6]}")
                
                st.markdown("---")
                
                confirm = st.checkbox("I confirm that I want to delete this product")
                
                if st.button("🗑️ Delete Product", type="primary", disabled=not confirm, use_container_width=True):
                    success, message = delete_product(sku_code)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
    
    # Stock Management
    elif menu == "📈 Stock Management":
        st.header("Stock Management")
        
        df = get_all_products()
        
        if len(df) == 0:
            st.warning("No products available!")
            return
        
        tab1, tab2 = st.tabs(["Quick Stock Update", "Bulk Stock Update"])
        
        with tab1:
            st.subheader("Quick Stock Adjustment")
            
            # Select product
            product_options = [f"{row['sku_code']} - {row['name']} (Current: {row['quantity']})" 
                             for _, row in df.iterrows()]
            selected_product = st.selectbox("Select Product", product_options)
            
            if selected_product:
                sku_code = selected_product.split(' - ')[0]
                product = get_product_by_sku(sku_code)
                
                st.markdown(f"**Current Stock:** {product[6]} units")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    add_quantity = st.number_input("Add Stock", min_value=0, step=1, value=0)
                    if st.button("➕ Add Stock", use_container_width=True):
                        if add_quantity > 0:
                            success, message = update_stock(sku_code, add_quantity)
                            if success:
                                st.success(f"Added {add_quantity} units!")
                                st.rerun()
                            else:
                                st.error(message)
                
                with col2:
                    remove_quantity = st.number_input("Remove Stock", min_value=0, step=1, value=0)
                    if st.button("➖ Remove Stock", use_container_width=True):
                        if remove_quantity > 0:
                            success, message = update_stock(sku_code, -remove_quantity)
                            if success:
                                st.success(f"Removed {remove_quantity} units!")
                                st.rerun()
                            else:
                                st.error(message)
        
        with tab2:
            st.subheader("Bulk Stock Update")
            st.info("Update stock for multiple products at once")
            
            # Create editable dataframe
            edit_df = df[['sku_code', 'name', 'weight', 'quantity']].copy()
            edit_df.columns = ['SKU Code', 'Product Name', 'Weight', 'Current Quantity']
            edit_df['New Quantity'] = edit_df['Current Quantity']
            
            edited_df = st.data_editor(
                edit_df[['SKU Code', 'Product Name', 'Weight', 'Current Quantity', 'New Quantity']],
                disabled=['SKU Code', 'Product Name', 'Weight', 'Current Quantity'],
                use_container_width=True,
                hide_index=True
            )
            
            if st.button("💾 Save All Changes", use_container_width=True):
                updates_made = 0
                for idx, row in edited_df.iterrows():
                    if row['New Quantity'] != row['Current Quantity']:
                        change = row['New Quantity'] - row['Current Quantity']
                        success, _ = update_stock(row['SKU Code'], change)
                        if success:
                            updates_made += 1
                
                if updates_made > 0:
                    st.success(f"Successfully updated {updates_made} products!")
                    st.rerun()
                else:
                    st.info("No changes detected")
    
    # Bulk Upload
    elif menu == "📥 Bulk Upload":
        st.header("Bulk Upload Products")
        
        st.markdown("""
        ### Instructions:
        1. Download the CSV template
        2. Fill in product details
        3. Upload the completed CSV file
        
        **CSV Format:**
        - SKU Code, Name, Description, Weight, Price, Quantity, Category, Pre-order Only (0 or 1)
        """)
        
        # Download template
        template_df = pd.DataFrame({
            'sku_code': ['210650'],
            'name': ['Sample Product'],
            'description': ['Product description here'],
            'weight': ['500g'],
            'price': [50],
            'quantity': [0],
            'category': ['BATTERS'],
            'pre_order_only': [0]
        })
        
        csv_template = template_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download CSV Template",
            data=csv_template,
            file_name="product_upload_template.csv",
            mime="text/csv"
        )
        
        st.markdown("---")
        
        # Upload CSV
        uploaded_file = st.file_uploader("Upload CSV File", type=['csv'])
        
        if uploaded_file is not None:
            try:
                upload_df = pd.read_csv(uploaded_file)
                
                st.markdown("### Preview")
                st.dataframe(upload_df, use_container_width=True)
                
                if st.button("📤 Upload All Products", use_container_width=True):
                    success_count = 0
                    error_count = 0
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for idx, row in upload_df.iterrows():
                        try:
                            success, message = add_product(
                                row['sku_code'],
                                row['name'],
                                row['description'],
                                row['weight'],
                                float(row['price']),
                                int(row['quantity']),
                                row['category'],
                                "",
                                int(row['pre_order_only'])
                            )
                            if success:
                                success_count += 1
                            else:
                                error_count += 1
                        except Exception as e:
                            error_count += 1
                        
                        progress = (idx + 1) / len(upload_df)
                        progress_bar.progress(progress)
                        status_text.text(f"Processing: {idx + 1}/{len(upload_df)}")
                    
                    st.success(f"✅ Successfully uploaded: {success_count} products")
                    if error_count > 0:
                        st.warning(f"⚠️ Failed to upload: {error_count} products (possibly duplicates)")
                    
                    st.balloons()
            
            except Exception as e:
                st.error(f"Error reading CSV file: {str(e)}")

if __name__ == "__main__":
    main()