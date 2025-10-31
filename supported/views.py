from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
import json
import os
import math
import pandas as pd


from django.http import FileResponse
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet




def main(request):
    return render(request, "supported.html")

class Supported:

    def __init__(self,span, load, fy,section_name, beam_type, unitCost = 38):
        self.span = span
        self.load = load
        self.fy = fy
        self.section_name = section_name
        self.beam_type = beam_type
        self.unitCost = unitCost

    def iscode(self):
        df = pd.read_csv(r'supported/static/beams.csv')
        for i in range(len(df)):
            if df['Section '][i] == self.section_name:
                D = df['D(mm)'][i]
                tw = df['tw(mm)'][i]
                bf = df['bf(mm)'][i]
                tf = df['tf(mm)'][i]
                R = df['R(mm)'][i]
                Iy = df['Iy(cm4)'][i]*1e4  # convert to mm^4
                ry = df['ry(cm)'][i]*10  # convert to mm
                Ze = df['Zex(cm3)'][i]*1e3  # convert to mm^3
                Zpz = df['Zpx(cm3)'][i]*1e3  # convert to mm^3
                Ixx = df['Ix(cm4)'][i]*1e4  # convert to mm^4
                return tw, D, bf, tf, R, Iy, ry, Ze, Zpz, Ixx

    def classify_section(self):

        tw, D, bf, tf, R, Iy, ry, Ze, Zpz, Ixx = self.iscode()
        epsilon = math.sqrt(250 / self.fy)

        # Web slenderness limits
        web_limit_plastic = 84 * epsilon
        web_limit_compact = 105 * epsilon
        web_limit_semi_compact = 126 * epsilon
        d = D - (2 * (tf + R))
        web_ratio = d/tw

        # Flange slenderness limits
        flange_limit_plastic = 9.4 * epsilon
        flange_limit_compact = 10.5 * epsilon
        flange_limit_semi_compact = 15.7 * epsilon
        flange_ratio = (bf / 2) / tf

        # Determine classification based on most governing limit
        if web_ratio <= web_limit_plastic and flange_ratio <= flange_limit_plastic:
            return "Plastic"
        elif web_ratio <= web_limit_compact and flange_ratio <= flange_limit_compact:
            return "Compact"
        elif web_ratio <= web_limit_semi_compact and flange_ratio <= flange_limit_semi_compact:
            return "Semi-Compact"
        else:
            return "Slender"

    def design_laterally_supported_beam(self):

        # Determine section classification
        tw, D, bf, tf, R, Iy, ry, Ze, Zpz, Ixx = self.iscode()
        section_class = self.classify_section()

        gamma_m0 = 1.1  # Partial safety factor for material

        if self.beam_type == "simply_supported":
            V_u = 1.5 * (self.load * self.span) / 2  # kN
        elif self.beam_type == "cantilever":
            V_u = 1.5 * self.load * self.span  # kN
        else:
            return {"Error": "Unsupported beam type"}

        # Shear strength check
        V_d = (self.fy * tw * D) / (1000 * gamma_m0 * math.sqrt(3))  # kN (Design shear strength)
        shear_check = "Safe" if V_u <= V_d else "Not Safe"

        is_low_shear = V_u <= 0.6 * V_d

        # Maximum bending moment (assuming UDL)
        if self.beam_type == "simply_supported":
            M_u = 1.5 * (self.load * self.span ** 2) / 8  # kN-m
        elif self.beam_type == "cantilever":
            M_u = 1.5 * (self.load * self.span ** 2) / 2  # kN-m
        M_u_Nmm = M_u * 10 ** 6  # Convert to N-mm

        # Determine design moment capacity based on section classification
        if section_class == "Plastic":
            Mp = (Zpz * self.fy) / gamma_m0  # N-mm
        elif section_class in ["Compact", "Semi-Compact"]:
            Mp = (Ze * self.fy) / gamma_m0  # N-mm
        else:
            return {
                "Section Name": self.section_name,
                "Section Classification": section_class,
                "Message": "Section is Slender and not suitable for bending"
            }

        # Bending strength check
        bending_check = "Safe" if Mp >= M_u_Nmm else "Not Safe"

        # Deflection Check
        E = 2e5  # MPa (Modulus of Elasticity of Steel)
        I = Ixx  # mm^4
        w = self.load  # N/mm

        if self.beam_type == "simply_supported":
            delta_max = (5 * w * ((self.span * 1000)**4) ) / (384 * E * I)  # mm
        elif self.beam_type == "cantilever":
            delta_max = ( w * ((self.span * 1000)**4) )/(8 * E * I)  # mm
            print(f"Load (w): {w} N/mm")
            print(f"Span (self.span): {self.span} m")
            print(f"Modulus of Elasticity (E): {E} MPa")
            print(f"Moment of Inertia (I): {I} mm^4")

        if self.beam_type == "simply_supported":
            deflection_limit = (self.span * 1000) / 300
        elif self.beam_type == "cantilever":
            deflection_limit = (self.span * 1000) / 150

        deflection_check = "Safe" if delta_max <= deflection_limit else "Not Safe"

        result =  {
            "section_name": self.section_name,
            "Beam_Type": self.beam_type,
            "Section_Classification": section_class,
            "Low_Shear_Condition": "Yes" if is_low_shear else "No",
            "Maximum_Bending_Moment": round(M_u, 2),
            "Design_Moment_Capacity": round(Mp / 10 ** 6, 2),
            "Bending_Strength_Check": bending_check,
            "Shear_Force": round(V_u, 2),
            "Design_Shear_Capacity": round(V_d, 2),
            "Shear_Strength_Check": shear_check,
            "Deflection_Limit":deflection_limit,
            "Maximum_Deflection": delta_max,
            "Deflection_Check": deflection_check,
            "span":self.span,
            "load":self.load,
            "fy":self.fy,
        }
        return result

    # def cost(self):
        # cost = self.unitCost * self.span * Ws


def solve(request):
    if request.method == 'POST':
        span = float(request.POST.get('span'))
        load = float(request.POST.get('load'))
        fy = float(request.POST.get('fy'))
        section_name = request.POST.get('section_name')
        beam_type = request.POST.get('beam_type')


        supported = Supported(span, load, fy,section_name, beam_type)
        result = supported.design_laterally_supported_beam()

        return render(request, "supported.html", result)
    return render(request,"supported.html")


def optimize_cost(request):
    if request.method == "POST":
        unit_cost = float(request.POST.get("unit_cost", 0))
        saved_data = json.loads(request.POST.get("beamMemory", "[]"))
        cost_results = []

        # ✅ Use a safer, dynamic path
        # csv_path = os.path.join(settings.BASE_DIR, 'unsupported', 'static', 'beams.csv')
        # df = pd.read_csv(csv_path)
        df = pd.read_csv(r'supported/static/beams.csv')

        for item in saved_data:
            section = item.get("section_name")
            span = float(item.get("span", 0))
            load = float(item.get("load", 0))
            moment = float(item.get("Design_Moment_Capacity", 0))
            max_moment = float(item.get("Maximum_Bending_Moment", 0))

            Ws = 0
            for i in range(len(df)):
                if df['Section '][i] == section:
                    Ws = df['Sectional Weight(kg/m)'][i]
                    break



            cost = Ws * span * unit_cost
            ur = (max_moment / moment) if moment else 0
            CO2 = 2 * Ws * span

            cost_results.append({
                "section_name": section,
                "Load": load,
                "span": span,
                "cost": cost,
                "ur": ur,
                "CO2": CO2,
            })

        # 1. Get the Minimum Cost and its corresponding item
        min_cost_item = min(cost_results, key=lambda x: x['cost'])
        min_cost = min_cost_item['cost']

        # 2. Get the Maximum Cost and its corresponding item
        max_cost_item = max(cost_results, key=lambda x: x['cost'])
        max_cost = max_cost_item['cost']

        # max carbon
        max_carbon_item = max(cost_results, key=lambda x: x['CO2'])
        max_carbon = max_carbon_item['CO2']

        ans = []

        for item in cost_results:
            section = item.get("section_name")
            span = float(item.get("span", 0))
            load = float(item.get("load", 0))

            result_item = next(
                (item for item in cost_results if item.get('section_name') == section),
                None
            )

            norm_cost = result_item['cost']/max_cost
            norm_carbon = result_item['CO2']/max_carbon
            norm_ur = abs(1- result_item['ur'])

            # final_score = norm_cost + norm_carbon + norm_ur

            ans.append({
                "section_name": section,
                "norm_cost": norm_cost,
                "norm_carbon": norm_carbon,
                "norm_ur": norm_ur,
                # "final_score": final_score,
            })





        context = {
            "cost_results": cost_results,
            "unit_cost": unit_cost,
            "ans": ans,
        }
        return render(request, "supported.html", context)

    # GET request — show empty page
    return render(request, "supported.html")



# def download_report(request):
#     if request.method == "POST":
#         # Retrieve data (replace this with however you're storing the results)
#         # saved_data = json.loads(request.session.get("beamMemory", "[]"))
#         saved_data = json.loads(request.POST.get("beamMemory", "[]"))
#
#
#         buffer = BytesIO()
#         p = canvas.Canvas(buffer, pagesize=A4)
#         width, height = A4
#         y = height - 50
#
#         p.setFont("Helvetica-Bold", 16)
#         p.drawString(180, y, "Laterally Supported Beam Design Report")
#         y -= 40
#         p.setFont("Helvetica", 12)
#
#         if not saved_data:
#             p.drawString(100, y, "No beam data available. Please calculate before downloading.")
#         else:
#             # Summary of all sections
#             best_section = min(saved_data, key=lambda x: x.get("Cost", 999999))
#             worst_section = max(saved_data, key=lambda x: x.get("Cost", 0))
#
#             p.drawString(50, y, f"Total Sections Evaluated: {len(saved_data)}")
#             y -= 20
#             p.drawString(50, y, f"Most Recommended Section: {best_section.get('section_name', 'N/A')}")
#             y -= 20
#             p.drawString(50, y, f"Least Recommended Section: {worst_section.get('section_name', 'N/A')}")
#             y -= 40
#
#             p.setFont("Helvetica-Bold", 13)
#             p.drawString(50, y, "Detailed Section Summary:")
#             y -= 20
#             p.setFont("Helvetica", 11)
#
#             for item in saved_data:
#                 if y < 100:  # new page if space ends
#                     p.showPage()
#                     p.setFont("Helvetica", 11)
#                     y = height - 60
#                 p.drawString(60, y, f"Section: {item.get('section_name','')} | Span: {item.get('span','')} | Load: {item.get('load','')}")
#                 y -= 15
#                 p.drawString(60, y, f"Moment: {item.get('Design_Moment','')} | Stress: {item.get('Stress','')} | Cost: ₹{item.get('Cost','')}")
#                 y -= 25
#
#         p.showPage()
#         p.save()
#         buffer.seek(0)
#
#         return FileResponse(buffer, as_attachment=True, filename="Beam_Design_Report.pdf")
#     return FileResponse(status=400)
#
#
#
#
# from django.http import FileResponse, JsonResponse
# from io import BytesIO
# from reportlab.lib.pagesizes import A4
# from reportlab.pdfgen import canvas
# from reportlab.lib import colors
# import json
#










def clear_data(request):
    if request.method == "POST":
        # Clear saved beam data from session
        if "beamMemory" in request.session:
            del request.session["beamMemory"]
        return JsonResponse({"status": "cleared"})
    return JsonResponse({"status": "invalid"}, status=400)


# def download_report(request):
#     from io import BytesIO
#     from django.http import FileResponse
#     from reportlab.lib.pagesizes import A4
#     from reportlab.pdfgen import canvas
#     import json
#
#     # 1️⃣ Try to get data from POST
#     if request.method == "POST" and request.POST.get("beamData"):
#         try:
#             saved_data = json.loads(request.POST.get("beamData"))
#         except Exception:
#             saved_data = []
#     else:
#         # fallback to session
#         saved_data = json.loads(request.session.get("beamMemory", "[]"))
#
#     # 2️⃣ If still empty
#     if not saved_data:
#         buffer = BytesIO()
#         p = canvas.Canvas(buffer, pagesize=A4)
#         p.setFont("Helvetica-Bold", 14)
#         p.drawString(150, 750, "Laterally Supported Beam Design Report")
#         p.setFont("Helvetica", 12)
#         p.drawString(150, 720, "No data available to generate report.")
#         p.save()
#         buffer.seek(0)
#         return FileResponse(buffer, as_attachment=True, filename="Beam_Design_Report.pdf")
#
#     # 3️⃣ Create report
#     buffer = BytesIO()
#     p = canvas.Canvas(buffer, pagesize=A4)
#     width, height = A4
#     y = height - 50
#
#     p.setFont("Helvetica-Bold", 16)
#     p.drawString(150, y, "Laterally Supported Beam Design Report")
#     y -= 40
#     p.setFont("Helvetica", 12)
#
#     # Compute best and worst
#     def safe_float(x):
#         try: return float(x)
#         except: return 999999
#     best_section = min(saved_data, key=lambda x: safe_float(x.get("Cost", 999999)))
#     worst_section = max(saved_data, key=lambda x: safe_float(x.get("Cost", 0)))
#
#     p.drawString(50, y, f"Total Sections Evaluated: {len(saved_data)}")
#     y -= 20
#     p.drawString(50, y, f"Best Section: {best_section.get('section_name', 'N/A')}")
#     y -= 20
#     p.drawString(50, y, f"Least Recommended: {worst_section.get('section_name', 'N/A')}")
#     y -= 30
#
#     p.setFont("Helvetica-Bold", 12)
#     p.drawString(50, y, "Section")
#     p.drawString(150, y, "Span")
#     p.drawString(230, y, "Load")
#     p.drawString(320, y, "Moment")
#     p.drawString(420, y, "Stress")
#     p.drawString(500, y, "Cost")
#     y -= 15
#     p.line(45, y, 550, y)
#     y -= 10
#
#     p.setFont("Helvetica", 10)
#     for item in saved_data:
#         if y < 60:
#             p.showPage()
#             y = height - 60
#             p.setFont("Helvetica", 10)
#         p.drawString(50, y, str(item.get("section_name", "")))
#         p.drawRightString(190, y, str(item.get("span", "")))
#         p.drawRightString(280, y, str(item.get("load", "")))
#         p.drawRightString(380, y, str(item.get("Design_Moment", "")))
#         p.drawRightString(470, y, str(item.get("Stress", "")))
#         p.drawRightString(550, y, str(item.get("Cost", "")))
#         y -= 15
#
#     p.showPage()
#     p.save()
#     buffer.seek(0)
#     return FileResponse(buffer, as_attachment=True, filename="Beam_Design_Report.pdf")








def download_report(request):
    # 1️⃣ Parse POST or session data
    if request.method == "POST" and request.POST.get("reportData"):
        try:
            report_data = json.loads(request.POST.get("reportData"))
        except Exception:
            report_data = {}
    else:
        report_data = json.loads(request.session.get("beamMemory", "{}"))

    # 2️⃣ Extract values
    calculations = report_data.get("calculations", {})
    tables = report_data.get("tables", {})
    generatedOn = report_data.get("generatedOn", "")

    # 3️⃣ Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph("<b>Laterally Supported Beam Design Report</b>", styles['Title']))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Generated on: {generatedOn}", styles['Normal']))
    story.append(Spacer(1, 20))

    # --- SECTION 1: INPUTS & CALCULATIONS ---
    if calculations:
        story.append(Paragraph("<b>1. Design Calculations Summary</b>", styles['Heading2']))
        data = [["Parameter", "Value"]] + [[k.replace("_", " ").title(), str(v)] for k, v in calculations.items()]
        calc_table = Table(data, colWidths=[200, 300])
        calc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        story.append(calc_table)
        story.append(Spacer(1, 20))

    # --- SECTION 2: TABLES ---
    if tables:
        story.append(Paragraph("<b>2. Design Results Tables</b>", styles['Heading2']))
        for name, rows in tables.items():
            story.append(Paragraph(f"<b>Table: {name}</b>", styles['Heading3']))
            if len(rows) > 0:
                headers = list(rows[0].keys())
                data = [headers]
                for row in rows:
                    data.append([row.get(h, "") for h in headers])
                tbl = Table(data, repeatRows=1)
                tbl.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ]))
                story.append(tbl)
                story.append(Spacer(1, 15))
            else:
                story.append(Paragraph("No data found in this table.", styles['Normal']))
                story.append(Spacer(1, 10))

    # --- SECTION 3: SUMMARY & RECOMMENDATION ---
    all_sections = []
    for t in tables.values():
        for row in t:
            if "Cost" in row:
                try:
                    all_sections.append((row.get("section_name", ""), float(row.get("Cost", 0))))
                except:
                    pass

    if all_sections:
        best = min(all_sections, key=lambda x: x[1])
        worst = max(all_sections, key=lambda x: x[1])
        story.append(Spacer(1, 20))
        story.append(Paragraph("<b>3. Recommendation</b>", styles['Heading2']))
        story.append(Paragraph(f"✅ <b>Best Section:</b> {best[0]} (Lowest cost: {best[1]:.2f})", styles['Normal']))
        story.append(Paragraph(f"⚠️ <b>Least Recommended:</b> {worst[0]} (Highest cost: {worst[1]:.2f})", styles['Normal']))

    story.append(Spacer(1, 30))
    story.append(Paragraph("Report Generated by Laterally Supported Beam Calculator", styles['Italic']))

    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename="Beam_Design_Report.pdf")
