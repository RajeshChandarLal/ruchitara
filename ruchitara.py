import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import datetime
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import qrcode
import json
import os

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
    .sticker-preview {
        border: 2px dashed #ccc;
        padding: 20px;
        border-radius: 10px;
        background-color: #f9f9f9;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Database Configuration Management
def load_db_config():
    """Load database configuration from file or environment"""
    config_file = 'db_config.json'
    
    # Try to load from file first
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    
    # Default configuration (can be overridden)
    return {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'ruchitara_inventory'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'postgres')
    }

def save_db_config(config):
    """Save database configuration to file"""
    config_file = 'db_config.json'
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=4)

# Database Connection
def get_db_connection():
    """Create database connection"""
    try:
        config = load_db_config()
        conn = psycopg2.connect(
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password']
        )
        return conn
    except Exception as e:
        st.error(f"Database connection error: {str(e)}")
        return None

# Database initialization
def init_db():
    """Initialize PostgreSQL database with products table"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        c = conn.cursor()
        
        # Create products table
        c.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                sku_code VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                weight VARCHAR(50),
                price DECIMAL(10, 2) NOT NULL,
                quantity INTEGER DEFAULT 0,
                category VARCHAR(100) NOT NULL,
                image_data BYTEA,
                image_filename VARCHAR(255),
                pre_order_only BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create index on sku_code for faster lookups
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_sku_code ON products(sku_code)
        ''')
        
        # Create index on category for faster filtering
        c.execute('''
            CREATE INDEX IF NOT EXISTS idx_category ON products(category)
        ''')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error initializing database: {str(e)}")
        if conn:
            conn.close()
        return False

# Image handling functions
def image_to_binary(image_file):
    """Convert image file to binary data"""
    if image_file is None:
        return None, None
    
    try:
        image = Image.open(image_file)
        # Resize image to reasonable size (max 800x800)
        image.thumbnail((800, 800), Image.Resampling.LANCZOS)
        
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        return buffered.getvalue(), image_file.name
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return None, None

def binary_to_image(binary_data):
    """Convert binary data to PIL Image"""
    if binary_data is None:
        return None
    
    try:
        return Image.open(BytesIO(binary_data))
    except Exception as e:
        st.error(f"Error loading image: {str(e)}")
        return None

def image_to_base64(image):
    """Convert PIL Image to base64 string"""
    if image is None:
        return None
    
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# CRUD Operations
def add_product(sku_code, name, description, weight, price, quantity, category, image_file=None, pre_order_only=False):
    """Add a new product to the database"""
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        c = conn.cursor()
        
        image_data, image_filename = image_to_binary(image_file)
        
        c.execute('''
            INSERT INTO products (sku_code, name, description, weight, price, quantity, category, image_data, image_filename, pre_order_only)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (sku_code, name, description, weight, price, quantity, category, image_data, image_filename, pre_order_only))
        
        conn.commit()
        conn.close()
        return True, "Product added successfully!"
    except psycopg2.IntegrityError:
        if conn:
            conn.close()
        return False, "Product with this SKU code already exists!"
    except Exception as e:
        if conn:
            conn.close()
        return False, f"Error: {str(e)}"

def get_all_products():
    """Retrieve all products from database"""
    conn = get_db_connection()
    if not conn:
        return pd.DataFrame()
    
    try:
        query = "SELECT id, sku_code, name, description, weight, price, quantity, category, image_filename, pre_order_only, last_updated FROM products ORDER BY category, name"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error fetching products: {str(e)}")
        if conn:
            conn.close()
        return pd.DataFrame()

def get_product_by_sku(sku_code):
    """Get a specific product by SKU code"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        c = conn.cursor(cursor_factory=RealDictCursor)
        c.execute("SELECT * FROM products WHERE sku_code = %s", (sku_code,))
        product = c.fetchone()
        conn.close()
        return product
    except Exception as e:
        st.error(f"Error fetching product: {str(e)}")
        if conn:
            conn.close()
        return None

def update_product(sku_code, name, description, weight, price, quantity, category, image_file=None, pre_order_only=False, update_image=False):
    """Update existing product"""
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        c = conn.cursor()
        
        if update_image and image_file:
            image_data, image_filename = image_to_binary(image_file)
            c.execute('''
                UPDATE products 
                SET name=%s, description=%s, weight=%s, price=%s, quantity=%s, category=%s, 
                    image_data=%s, image_filename=%s, pre_order_only=%s, last_updated=%s
                WHERE sku_code=%s
            ''', (name, description, weight, price, quantity, category, image_data, image_filename, pre_order_only, datetime.now(), sku_code))
        else:
            c.execute('''
                UPDATE products 
                SET name=%s, description=%s, weight=%s, price=%s, quantity=%s, category=%s, pre_order_only=%s, last_updated=%s
                WHERE sku_code=%s
            ''', (name, description, weight, price, quantity, category, pre_order_only, datetime.now(), sku_code))
        
        conn.commit()
        conn.close()
        return True, "Product updated successfully!"
    except Exception as e:
        if conn:
            conn.close()
        return False, f"Error: {str(e)}"

def delete_product(sku_code):
    """Delete a product from database"""
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        c = conn.cursor()
        c.execute("DELETE FROM products WHERE sku_code = %s", (sku_code,))
        conn.commit()
        conn.close()
        return True, "Product deleted successfully!"
    except Exception as e:
        if conn:
            conn.close()
        return False, f"Error: {str(e)}"

def update_stock(sku_code, quantity_change):
    """Update stock quantity (add or subtract)"""
    conn = get_db_connection()
    if not conn:
        return False, "Database connection failed"
    
    try:
        c = conn.cursor()
        c.execute('''
            UPDATE products 
            SET quantity = quantity + %s, last_updated = %s
            WHERE sku_code = %s
        ''', (quantity_change, datetime.now(), sku_code))
        conn.commit()
        conn.close()
        return True, "Stock updated successfully!"
    except Exception as e:
        if conn:
            conn.close()
        return False, f"Error: {str(e)}"

def get_categories():
    """Get all unique categories"""
    conn = get_db_connection()
    if not conn:
        return []
    
    try:
        c = conn.cursor()
        c.execute("SELECT DISTINCT category FROM products ORDER BY category")
        categories = [row[0] for row in c.fetchall()]
        conn.close()
        return categories
    except Exception as e:
        st.error(f"Error fetching categories: {str(e)}")
        if conn:
            conn.close()
        return []

def get_stats():
    """Get inventory statistics"""
    conn = get_db_connection()
    if not conn:
        return {
            'total_products': 0,
            'low_stock': 0,
            'total_value': 0,
            'out_of_stock': 0
        }
    
    try:
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
            'total_value': float(total_value),
            'out_of_stock': out_of_stock
        }
    except Exception as e:
        st.error(f"Error fetching stats: {str(e)}")
        if conn:
            conn.close()
        return {
            'total_products': 0,
            'low_stock': 0,
            'total_value': 0,
            'out_of_stock': 0
        }

# Sticker Generation Functions
def create_sticker(product, size_preset, include_qr=True, include_price=True, include_expiry=True, expiry_date=None):
    """
    Generate product sticker with customizable options
    
    size_preset: 'small' (2x1 inch), 'medium' (3x2 inch), 'large' (4x3 inch), 'custom'
    """
    # Size presets in pixels (300 DPI)
    sizes = {
        'small': (600, 300),   # 2x1 inch @ 300 DPI
        'medium': (900, 600),  # 3x2 inch @ 300 DPI
        'large': (1200, 900),  # 4x3 inch @ 300 DPI
    }
    
    if size_preset in sizes:
        width, height = sizes[size_preset]
    else:
        width, height = (900, 600)  # Default to medium
    
    # Create blank sticker
    sticker = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(sticker)
    
    # Try to use system fonts, fallback to default
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size=int(height * 0.08))
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=int(height * 0.06))
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=int(height * 0.045))
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Border
    draw.rectangle([(5, 5), (width-5, height-5)], outline='black', width=3)
    
    # Layout
    y_offset = 20
    x_margin = 20
    
    # Product image (if available)
    if product.get('image_data'):
        try:
            product_image = binary_to_image(product['image_data'])
            if product_image:
                img_size = int(height * 0.35)
                product_image.thumbnail((img_size, img_size), Image.Resampling.LANCZOS)
                sticker.paste(product_image, (x_margin, y_offset))
                y_offset += img_size + 10
        except:
            pass
    
    # Company name
    draw.text((x_margin, y_offset), "RUCHITARA FOODS", fill='#2E7D32', font=font_medium)
    y_offset += int(height * 0.08)
    
    # Product name (word wrap if needed)
    product_name = product['name']
    if len(product_name) > 30:
        words = product_name.split()
        line1 = ' '.join(words[:len(words)//2])
        line2 = ' '.join(words[len(words)//2:])
        draw.text((x_margin, y_offset), line1, fill='black', font=font_large)
        y_offset += int(height * 0.09)
        draw.text((x_margin, y_offset), line2, fill='black', font=font_large)
        y_offset += int(height * 0.09)
    else:
        draw.text((x_margin, y_offset), product_name, fill='black', font=font_large)
        y_offset += int(height * 0.1)
    
    # Weight
    draw.text((x_margin, y_offset), f"Weight: {product['weight']}", fill='black', font=font_medium)
    y_offset += int(height * 0.07)
    
    # Price (if included)
    if include_price:
        price_text = f"MRP ₹ {product['price']:.2f} INC.TAX"
        draw.text((x_margin, y_offset), price_text, fill='black', font=font_large)
        y_offset += int(height * 0.09)
    
    # Expiry date (if included)
    if include_expiry and expiry_date:
        expiry_text = f"EXPIRY {expiry_date}"
        draw.text((x_margin, y_offset), expiry_text, fill='red', font=font_medium)
        y_offset += int(height * 0.07)
    
    # SKU Code (barcode-like text)
    draw.text((x_margin, y_offset), f"SKU: {product['sku_code']}", fill='black', font=font_small)
    y_offset += int(height * 0.06)
    
    # QR Code (if included)
    if include_qr:
        qr_data = f"SKU:{product['sku_code']}\nName:{product['name']}\nPrice:{product['price']}\nWeight:{product['weight']}"
        qr = qrcode.QRCode(version=1, box_size=3, border=1)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        qr_size = int(height * 0.25)
        qr_image = qr_image.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
        
        # Position QR code in bottom right
        qr_x = width - qr_size - x_margin
        qr_y = height - qr_size - 20
        sticker.paste(qr_image, (qr_x, qr_y))
    
    # Manufacturing info
    mfg_text = f"MFG 24/11/25"
    draw.text((x_margin, height - 60), mfg_text, fill='black', font=font_small)
    
    # Batch number
    batch_text = f"BATCH: 0141125"
    draw.text((x_margin, height - 35), batch_text, fill='black', font=font_small)
    
    return sticker

def load_initial_products():
    """Load initial product data from RUCHITARA catalog"""
    
    # Check if products already exist
    df = get_all_products()
    if len(df) > 0:
        return
    
    # BATTERS - Regular products
    batters = [
        ("210610", "Dosa Batter", "Traditional dosa batter for crispy dosas", "500g", 50, 0, "BATTERS", False),
        ("210611", "Idli Batter", "Soft and fluffy idli batter", "500g", 50, 0, "BATTERS", False),
        ("210612", "Wada Batter", "Perfect wada batter (Pre-order only)", "1kg", 125, 0, "BATTERS", True),
        ("210613", "Green Gram Batter", "Nutritious green gram batter (Pre-order only)", "500g", 50, 0, "BATTERS", True),
        ("210614", "Finger Millet Dosa Batter (Ragi Dosa)", "Healthy ragi dosa batter", "500g", 55, 0, "BATTERS", False),
        ("210615", "Finger Millet Idli Batter (Ragi Idli)", "Healthy ragi idli batter", "500g", 55, 0, "BATTERS", False),
        ("210616", "Foxtail Millet Dosa Batter (Korra Dosa)", "Nutritious foxtail millet dosa", "500g", 55, 0, "BATTERS", False),
        ("210617", "Foxtail Millet Idli Batter (Korra Idli)", "Nutritious foxtail millet idli", "500g", 55, 0, "BATTERS", False),
    ]
    
    # SPICED POWDERS - Products with variants
    spiced_powders = [
        ("91010-100", "Flaxseed Spiced Powder", "Nutritious flaxseed spiced powder", "100g", 70, 0, "SPICED POWDERS", False),
        ("91010-250", "Flaxseed Spiced Powder", "Nutritious flaxseed spiced powder", "250g", 175, 0, "SPICED POWDERS", False),
        ("91011-100", "Peanuts Spiced Powder", "Crunchy peanuts spiced powder", "100g", 60, 0, "SPICED POWDERS", False),
        ("91011-250", "Peanuts Spiced Powder", "Crunchy peanuts spiced powder", "250g", 150, 0, "SPICED POWDERS", False),
    ]
    
    # Insert all products
    for product in batters + spiced_powders:
        add_product(*product)

# Main Application
def main():
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
             "🗑️ Delete Product", "📈 Stock Management", "🏷️ Generate Stickers", 
             "📥 Bulk Upload", "⚙️ Database Settings"]
        )
        
        st.markdown("---")
        st.markdown("### Contact Info")
        st.markdown("📞 8500 834 534")
        st.markdown("📞 94038 93333")
        st.markdown("📧 info@ruchitara.in")
        st.markdown("🏢 b2b@ruchitara.in")
    
    # Database Settings
    if menu == "⚙️ Database Settings":
        st.header("Database Configuration")
        
        st.info("Configure your PostgreSQL database connection here. Changes will be saved for future sessions.")
        
        current_config = load_db_config()
        
        with st.form("db_config_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                host = st.text_input("Database Host", value=current_config.get('host', 'localhost'))
                port = st.text_input("Database Port", value=current_config.get('port', '5432'))
                database = st.text_input("Database Name", value=current_config.get('database', 'ruchitara_inventory'))
            
            with col2:
                user = st.text_input("Database User", value=current_config.get('user', 'postgres'))
                password = st.text_input("Database Password", type="password", value=current_config.get('password', ''))
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                test_connection = st.form_submit_button("🔍 Test Connection", use_container_width=True)
            
            with col2:
                save_config = st.form_submit_button("💾 Save Configuration", use_container_width=True)
            
            with col3:
                initialize_db = st.form_submit_button("🚀 Initialize Database", use_container_width=True)
            
            if test_connection:
                try:
                    test_conn = psycopg2.connect(
                        host=host,
                        port=port,
                        database=database,
                        user=user,
                        password=password
                    )
                    test_conn.close()
                    st.success("✅ Database connection successful!")
                except Exception as e:
                    st.error(f"❌ Connection failed: {str(e)}")
            
            if save_config:
                new_config = {
                    'host': host,
                    'port': port,
                    'database': database,
                    'user': user,
                    'password': password
                }
                save_db_config(new_config)
                st.success("✅ Configuration saved successfully!")
                st.info("Please restart the application for changes to take effect.")
            
            if initialize_db:
                if init_db():
                    st.success("✅ Database initialized successfully!")
                    load_initial_products()
                    st.success("✅ Sample products loaded!")
                else:
                    st.error("❌ Failed to initialize database. Please check your configuration.")
        
        # Display SQL script
        st.markdown("---")
        st.subheader("📄 Database Setup Script")
        
        sql_script = '''-- PostgreSQL Database Setup Script for Ruchitara Foods Inventory

-- Create database (run this as postgres superuser)
-- CREATE DATABASE ruchitara_inventory;

-- Connect to the database
-- \\c ruchitara_inventory;

-- Create products table
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    sku_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    weight VARCHAR(50),
    price DECIMAL(10, 2) NOT NULL,
    quantity INTEGER DEFAULT 0,
    category VARCHAR(100) NOT NULL,
    image_data BYTEA,
    image_filename VARCHAR(255),
    pre_order_only BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_sku_code ON products(sku_code);
CREATE INDEX IF NOT EXISTS idx_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_quantity ON products(quantity);

-- Create trigger to update last_updated timestamp
CREATE OR REPLACE FUNCTION update_last_updated_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_products_last_updated 
    BEFORE UPDATE ON products 
    FOR EACH ROW 
    EXECUTE FUNCTION update_last_updated_column();

-- Sample query to verify setup
-- SELECT * FROM products LIMIT 10;'''
        
        st.code(sql_script, language='sql')
        
        st.download_button(
            label="📥 Download SQL Script",
            data=sql_script,
            file_name="setup_database.sql",
            mime="text/sql"
        )
        
        return
    
    # Initialize database (silent)
    if not init_db():
        st.error("⚠️ Database connection failed! Please configure your database in 'Database Settings'.")
        return
    
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
        
        if len(df) > 0:
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
        else:
            st.info("No products in inventory. Add products to get started!")
    
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
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    # Display product image if available
                    product_full = get_product_by_sku(row['sku_code'])
                    if product_full and product_full.get('image_data'):
                        image = binary_to_image(product_full['image_data'])
                        if image:
                            st.image(image, use_column_width=True)
                    else:
                        st.info("No image available")
                
                with col2:
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
            
            # Image upload
            st.markdown("**Product Image**")
            uploaded_file = st.file_uploader("Choose an image", type=['png', 'jpg', 'jpeg'])
            
            if uploaded_file is not None:
                image = Image.open(uploaded_file)
                st.image(image, caption="Preview", width=200)
            
            submitted = st.form_submit_button("Add Product", use_container_width=True)
            
            if submitted:
                if not sku_code or not name or not weight or price <= 0:
                    st.error("Please fill in all required fields marked with *")
                else:
                    success, message = add_product(
                        sku_code, name, description, weight, price, quantity, 
                        category, uploaded_file, pre_order_only
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
                # Display current image
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    if product.get('image_data'):
                        image = binary_to_image(product['image_data'])
                        if image:
                            st.image(image, caption="Current Image", use_column_width=True)
                    else:
                        st.info("No current image")
                
                with col2:
                    st.markdown(f"### Current Product: {product['name']}")
                    st.markdown(f"**SKU:** {product['sku_code']}")
                    st.markdown(f"**Category:** {product['category']}")
                
                with st.form("update_product_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.text_input("SKU Code", value=product['sku_code'], disabled=True)
                        name = st.text_input("Product Name*", value=product['name'])
                        weight = st.text_input("Weight*", value=product['weight'])
                        price = st.number_input("Price (₹)*", value=float(product['price']), min_value=0.0, step=0.5)
                    
                    with col2:
                        categories_list = ["BATTERS", "SPICED POWDERS", "OTHER"]
                        category_index = categories_list.index(product['category']) if product['category'] in categories_list else 0
                        category = st.selectbox("Category*", categories_list, index=category_index)
                        quantity = st.number_input("Quantity", value=int(product['quantity']), min_value=0, step=1)
                        pre_order_only = st.checkbox("Pre-order Only", value=bool(product['pre_order_only']))
                    
                    description = st.text_area("Description", value=product['description'] if product['description'] else "")
                    
                    # Image upload
                    st.markdown("**Update Product Image (Optional)**")
                    update_image_check = st.checkbox("Update Image")
                    uploaded_file = None
                    
                    if update_image_check:
                        uploaded_file = st.file_uploader("Choose an image", type=['png', 'jpg', 'jpeg'])
                        
                        if uploaded_file is not None:
                            image = Image.open(uploaded_file)
                            st.image(image, caption="New Preview", width=200)
                    
                    submitted = st.form_submit_button("Update Product", use_container_width=True)
                    
                    if submitted:
                        if not name or not weight or price <= 0:
                            st.error("Please fill in all required fields marked with *")
                        else:
                            success, message = update_product(
                                sku_code, name, description, weight, price, quantity, 
                                category, uploaded_file, pre_order_only, update_image_check
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
                
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    if product.get('image_data'):
                        image = binary_to_image(product['image_data'])
                        if image:
                            st.image(image, use_column_width=True)
                
                with col2:
                    st.markdown(f"**SKU Code:** {product['sku_code']}")
                    st.markdown(f"**Name:** {product['name']}")
                    st.markdown(f"**Category:** {product['category']}")
                    st.markdown(f"**Weight:** {product['weight']}")
                    st.markdown(f"**Price:** ₹{product['price']}")
                    st.markdown(f"**Quantity:** {product['quantity']}")
                
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
                
                st.markdown(f"**Current Stock:** {product['quantity']} units")
                
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
    
    # Generate Stickers
    elif menu == "🏷️ Generate Stickers":
        st.header("Generate Product Stickers")
        
        df = get_all_products()
        
        if len(df) == 0:
            st.warning("No products available!")
            return
        
        st.markdown("""
        ### Sticker Generator
        Create professional product stickers with customizable sizes and options.
        Perfect for labeling products, inventory management, and retail displays.
        """)
        
        # Sticker configuration
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Select product
            product_options = [f"{row['sku_code']} - {row['name']}" for _, row in df.iterrows()]
            selected_product = st.selectbox("Select Product", product_options)
            
            if selected_product:
                sku_code = selected_product.split(' - ')[0]
                product = get_product_by_sku(sku_code)
                
                if product:
                    # Sticker options
                    st.markdown("### Sticker Options")
                    
                    col_opt1, col_opt2, col_opt3 = st.columns(3)
                    
                    with col_opt1:
                        size_preset = st.selectbox("Sticker Size", 
                                                   ['small', 'medium', 'large'],
                                                   index=1,
                                                   help="Small: 2x1 inch, Medium: 3x2 inch, Large: 4x3 inch")
                    
                    with col_opt2:
                        include_qr = st.checkbox("Include QR Code", value=True)
                        include_price = st.checkbox("Include Price", value=True)
                    
                    with col_opt3:
                        include_expiry = st.checkbox("Include Expiry Date", value=True)
                        expiry_date = None
                        if include_expiry:
                            expiry_date = st.date_input("Expiry Date").strftime("%d/%m/%y")
                    
                    # Number of stickers
                    num_stickers = st.slider("Number of Stickers", min_value=1, max_value=50, value=1)
                    
                    if st.button("🏷️ Generate Stickers", use_container_width=True):
                        with st.spinner("Generating stickers..."):
                            # Generate sticker
                            sticker = create_sticker(
                                product, 
                                size_preset, 
                                include_qr, 
                                include_price, 
                                include_expiry, 
                                expiry_date
                            )
                            
                            # If multiple stickers, create a sheet
                            if num_stickers > 1:
                                # Calculate grid layout
                                cols = 3  # 3 stickers per row
                                rows = (num_stickers + cols - 1) // cols
                                
                                # Create sheet with margins
                                margin = 50
                                sheet_width = sticker.width * cols + margin * (cols + 1)
                                sheet_height = sticker.height * rows + margin * (rows + 1)
                                
                                sheet = Image.new('RGB', (sheet_width, sheet_height), 'white')
                                
                                for i in range(num_stickers):
                                    row = i // cols
                                    col = i % cols
                                    x = margin + col * (sticker.width + margin)
                                    y = margin + row * (sticker.height + margin)
                                    sheet.paste(sticker, (x, y))
                                
                                sticker = sheet
                            
                            # Display preview
                            with col2:
                                st.markdown("### Preview")
                                st.image(sticker, use_column_width=True)
                            
                            # Download options
                            st.markdown("---")
                            st.markdown("### Download Stickers")
                            
                            col_dl1, col_dl2 = st.columns(2)
                            
                            with col_dl1:
                                # PNG download
                                buffered = BytesIO()
                                sticker.save(buffered, format="PNG", dpi=(300, 300))
                                png_data = buffered.getvalue()
                                
                                st.download_button(
                                    label="📥 Download as PNG (High Quality)",
                                    data=png_data,
                                    file_name=f"sticker_{sku_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                                    mime="image/png",
                                    use_container_width=True
                                )
                            
                            with col_dl2:
                                # PDF download
                                pdf_buffer = BytesIO()
                                sticker_rgb = sticker.convert('RGB')
                                sticker_rgb.save(pdf_buffer, format="PDF", resolution=300.0)
                                pdf_data = pdf_buffer.getvalue()
                                
                                st.download_button(
                                    label="📥 Download as PDF",
                                    data=pdf_data,
                                    file_name=f"sticker_{sku_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                                    mime="application/pdf",
                                    use_container_width=True
                                )
                            
                            st.success(f"✅ Generated {num_stickers} sticker(s) successfully!")
        
        with col2:
            st.markdown("### Sticker Sizes")
            st.info("""
            **Small (2x1 inch)**
            - Compact design
            - Basic information
            - Ideal for small packages
            
            **Medium (3x2 inch)**
            - Standard size
            - All details included
            - Most versatile option
            
            **Large (4x3 inch)**
            - Extra visibility
            - Large QR code
            - Perfect for display
            """)
    
    # Bulk Upload
    elif menu == "📥 Bulk Upload":
        st.header("Bulk Upload Products")
        
        st.markdown("""
        ### Instructions:
        1. Download the CSV template
        2. Fill in product details
        3. Upload the completed CSV file
        
        **CSV Format:**
        - SKU Code, Name, Description, Weight, Price, Quantity, Category, Pre-order Only (TRUE/FALSE)
        """)
        
        # Download template
        template_df = pd.DataFrame({
            'sku_code': ['210650', '210651'],
            'name': ['Sample Product 1', 'Sample Product 2'],
            'description': ['Product description here', 'Another description'],
            'weight': ['500g', '1kg'],
            'price': [50, 100],
            'quantity': [0, 10],
            'category': ['BATTERS', 'SPICED POWDERS'],
            'pre_order_only': [False, True]
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
                    errors = []
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    for idx, row in upload_df.iterrows():
                        try:
                            pre_order = bool(row['pre_order_only']) if 'pre_order_only' in row else False
                            
                            success, message = add_product(
                                str(row['sku_code']),
                                str(row['name']),
                                str(row['description']),
                                str(row['weight']),
                                float(row['price']),
                                int(row['quantity']),
                                str(row['category']),
                                None,
                                pre_order
                            )
                            if success:
                                success_count += 1
                            else:
                                error_count += 1
                                errors.append(f"Row {idx+2}: {message}")
                        except Exception as e:
                            error_count += 1
                            errors.append(f"Row {idx+2}: {str(e)}")
                        
                        progress = (idx + 1) / len(upload_df)
                        progress_bar.progress(progress)
                        status_text.text(f"Processing: {idx + 1}/{len(upload_df)}")
                    
                    st.success(f"✅ Successfully uploaded: {success_count} products")
                    if error_count > 0:
                        st.warning(f"⚠️ Failed to upload: {error_count} products")
                        with st.expander("View Errors"):
                            for error in errors:
                                st.text(error)
                    
                    if success_count > 0:
                        st.balloons()
            
            except Exception as e:
                st.error(f"Error reading CSV file: {str(e)}")

if __name__ == "__main__":
    main()
