import matplotlib
matplotlib.use('Agg')  # Prevents GUI crashes on the server
import matplotlib.pyplot as plt
from fpdf import FPDF
import datetime
import os

def generate_comparison_chart(lake_name, current_ndci, current_lst):
    """Generates a bar chart comparing current readings to safe thresholds."""
    # Define thresholds
    safe_ndci = 0.10
    ambient_temp = 28.0 # Baseline safe city temp
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 4), dpi=200)
    
    # Chart 1: Chlorophyll (NDCI)
    colors_ndci = ['#2ecc71' if current_ndci <= safe_ndci else '#e74c3c', '#95a5a6']
    ax1.bar(['Current', 'Safe Limit'], [current_ndci, safe_ndci], color=colors_ndci)
    ax1.set_title('Algal Bloom Risk (NDCI)', fontweight='bold')
    ax1.set_ylabel('Index Value')
    ax1.axhline(safe_ndci, color='red', linestyle='--', alpha=0.5)
    
    # Chart 2: Temperature (LST)
    colors_lst = ['#e67e22' if current_lst > ambient_temp else '#3498db', '#95a5a6']
    ax2.bar(['Current LST', 'Ambient Temp'], [current_lst, ambient_temp], color=colors_lst)
    ax2.set_title('Thermal Anomaly (°C)', fontweight='bold')
    ax2.set_ylabel('Temperature (°C)')
    
    plt.suptitle(f'{lake_name} Lake: Current vs. Baseline Thresholds', fontweight='bold')
    plt.tight_layout()
    
    image_path = f"temp_chart_{lake_name}.png"
    plt.savefig(image_path)
    plt.close()
    
    return image_path

def create_pdf_report(lake_name, area, ndci, lst, ndti, mci, status, conclusion):
    """Compiles the text and the chart into a downloadable PDF."""
    chart_image = generate_comparison_chart(lake_name, ndci, lst)
    
    pdf = FPDF()
    pdf.add_page()
    
    # 1. Professional Header
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, txt="ENVIRONMENTAL TELEMETRY REPORT", ln=True, align='C')
    pdf.set_font("Arial", '', 11)
    pdf.cell(0, 6, txt="Automated Satellite Scan Results", ln=True, align='C')
    
    scan_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(0, 8, txt=f"Generated on: {scan_time}", ln=True, align='C')
    pdf.line(10, 35, 200, 35)
    pdf.ln(8)
    
    # 2. Target Info
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, txt=f"Target Water Body: {lake_name.capitalize()} Lake", ln=True)
    pdf.ln(2)
    
    # ---------------------------------------------------------
    # 3. THE "BLOOD REPORT" DATA TABLE
    # ---------------------------------------------------------
    # Table Header
    pdf.set_font("Arial", 'B', 11)
    pdf.set_fill_color(240, 240, 240) # Light grey background for header
    pdf.cell(65, 8, txt=" Parameter", border=1, fill=True)
    pdf.cell(60, 8, txt=" Detected Value", border=1, align='C', fill=True)
    pdf.cell(60, 8, txt=" Safe Threshold", border=1, align='C', fill=True)
    pdf.ln()
    
    # Table Rows
    pdf.set_font("Arial", '', 11)
    
    # Row 1: Area
    pdf.cell(65, 8, txt=" Total Surface Area", border=1)
    pdf.cell(60, 8, txt=f"{area} Ha", border=1, align='C')
    pdf.cell(60, 8, txt=" Dynamic", border=1, align='C')
    pdf.ln()
    
    # Row 2: LST (Temperature)
    pdf.cell(65, 8, txt=" Surface Temp (LST)", border=1)
    # Highlight red if too hot
    if float(lst) > 28.0:
        pdf.set_text_color(220, 53, 69)
        pdf.set_font("Arial", 'B', 11)
    pdf.cell(60, 8, txt=f"{lst} °C", border=1, align='C')
    pdf.set_text_color(0, 0, 0) # Reset
    pdf.set_font("Arial", '', 11) # Reset
    pdf.cell(60, 8, txt=" < 28.0 °C", border=1, align='C')
    pdf.ln()
    
    # Row 3: NDTI (Turbidity)
    pdf.cell(65, 8, txt=" Turbidity (NDTI)", border=1)
    if float(ndti) > 0.1:
        pdf.set_text_color(220, 53, 69)
        pdf.set_font("Arial", 'B', 11)
    pdf.cell(60, 8, txt=f"{ndti}", border=1, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 11)
    pdf.cell(60, 8, txt=" < 0.10", border=1, align='C')
    pdf.ln()
    
    # Row 4: NDCI (Chlorophyll)
    pdf.cell(65, 8, txt=" Chlorophyll Conc. (NDCI)", border=1)
    if float(ndci) > 0.1:
        pdf.set_text_color(220, 53, 69)
        pdf.set_font("Arial", 'B', 11)
    pdf.cell(60, 8, txt=f"{ndci}", border=1, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 11)
    pdf.cell(60, 8, txt=" < 0.10", border=1, align='C')
    pdf.ln()
    
    # Row 5: MCI (Algal Bloom)
    pdf.cell(65, 8, txt=" Algal Bloom (MCI)", border=1)
    if float(mci) > 0.05:
        pdf.set_text_color(220, 53, 69)
        pdf.set_font("Arial", 'B', 11)
    pdf.cell(60, 8, txt=f"{mci}", border=1, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 11)
    pdf.cell(60, 8, txt=" < 0.05", border=1, align='C')
    pdf.ln(8)
    # ---------------------------------------------------------
    
    # 4. Clean Status Formatting
    pdf.set_font("Arial", '', 11)
    pdf.write(8, "Overall Ecological Status: ")
    
    if "High" in status:
        pdf.set_text_color(220, 53, 69) # Red
    elif status == "Clear":
        pdf.set_text_color(40, 167, 69) # Green
    else:
        pdf.set_text_color(241, 196, 15) # Yellow
        
    pdf.set_font("Arial", 'B', 12) 
    pdf.write(8, status.upper())
    pdf.set_text_color(0, 0, 0)
    pdf.ln(12)
    
    # 5. Inject the AI Conclusion text
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 6, txt="Analysis Insight:", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 6, txt=conclusion)
    pdf.ln(10)
    
    # 6. Inject the Chart
    pdf.image(chart_image, x=20, y=145, w=170) 
    
    pdf_filename = f"{lake_name}_Telemetry_Report.pdf"
    pdf.output(pdf_filename)
    
    if os.path.exists(chart_image):
        os.remove(chart_image) 
        
    return pdf_filename