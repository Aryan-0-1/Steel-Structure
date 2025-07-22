from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
import math
import pandas as pd


def main(request):
    return render(request, "supported.html")

class Supported:

    def __init__(self,span, load, fy,section_name, beam_type):
        self.span = span
        self.load = load
        self.fy = fy
        self.section_name = section_name
        self.beam_type = beam_type

    def iscode(self):
        df = pd.read_csv('C:\\Users\\aryan\PycharmProjects\Steel\steel\\unsupported\static\\beams.csv')
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


