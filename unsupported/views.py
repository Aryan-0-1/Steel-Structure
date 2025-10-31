from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
import math
import pandas as pd


def main(request):
    return render(request, "unsupported.html")

class Unsupported:

    def __init__(self,span, load, fy, section_name, Llt, alpha,beam_type):
        self.span = span
        self.load = load
        self.fy = fy
        self.section_name = section_name
        self.Llt = Llt
        self.alpha = alpha
        self.beam_type = beam_type
        self.gamma_m0 = 1.1

    def iscode(self):
        df = pd.read_csv(r'unsupported\static\beams.csv')
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

    def classify_section(self, D, tw, bf, tf,R):
        epsilon = math.sqrt((250/self.fy))
        web_limit_plastic = 84 * epsilon
        web_limit_compact = 105 * epsilon
        web_limit_semi_compact = 126 * epsilon
        d = D - (2*(tf + R))
        web_ratio = d / tw
        flange_limit_plastic = 9.4 * epsilon
        flange_limit_compact = 10.5 * epsilon
        flange_limit_semi_compact = 15.7 * epsilon
        flange_ratio = (bf/2)/tf

        if web_ratio <= web_limit_plastic and flange_ratio <= flange_limit_plastic:
            return "Plastic"
        elif web_ratio <= web_limit_compact and flange_ratio <= flange_limit_compact:
            return "Compact"
        elif web_ratio <= web_limit_semi_compact and flange_ratio <= flange_limit_semi_compact:
            return "Semi-Compact"
        else:
            return "Slender"

    def calculate_Mcr(self,E, Iy, ry, D, tf):
        hf = D - tf
        term = (self.Llt * tf) / (ry * hf)
        Mcr = (((math.pi**2) * E * Iy * hf)/(2 * self.Llt ** 2)) * math.sqrt( (1+ ((1/20)*(term ** 2)) ) )
        return  Mcr

    def calculate_Xlt(self):
        E = 2e5  # MPa
        tw, D, bf, tf, R, Iy, ry, Ze, Zpz, Ixx = self.iscode()

        Mcr = self.calculate_Mcr(E, Iy, ry, D, tf)/1e6
        classify = self.classify_section(D, tw, bf, tf,R)
        if classify in ["Plastic", "Compact"]:
            beta_b = 1.0
        else:
            beta_b = Ze/Zpz

        lambda_LT = math.sqrt( (beta_b * Zpz * self.fy)/Mcr )
        phi = 0.5 * (1 + (self.alpha * (lambda_LT - 0.2))+ (lambda_LT ** 2))
        Xlt = 1 / (phi + math.sqrt((phi ** 2) - (lambda_LT ** 2)))
        return min(Xlt, 1)

    def design_bending_strength(self,section_class,Ze, Zpz):
        Xlt = self.calculate_Xlt()
        fbd = (Xlt * self.fy) / self.gamma_m0

        if section_class == "Plastic":
            beta_b = 1.0
            Zb = Zpz
        elif section_class == "Compact":
            beta_b = 1.0
            Zb = Ze
        elif section_class == "Semi-Compact":
            beta_b = Ze / Zpz
            Zb = Ze
        else:
            return None

        Md = (beta_b)*(Zb)*(fbd)  # N-mm
        return (Md/1e6)  # kN-m

    def design_laterally_unsupported_beam(self):
        gamma_m0 = 1.1
        E = 2e5  # MPa
        tw, D, bf, tf, R, Iy, ry, Ze, Zpz, Ixx = self.iscode()

        section_class = self.classify_section(D, tw, bf, tf, R)

        # Bending strength
        Md_kNm = self.design_bending_strength(section_class, Ze, Zpz)
        if Md_kNm is None:
            return {
                "Section Name": self.section_name,
                "Section Classification": section_class,
                "Message": "Slender section is not suitable for bending"
            }

        w = (self.load * 1000)/1000  # convert kN/m to N/mm
        L_mm = self.span * 1000

        # Calculate Mu and Vu based on beam type
        if self.beam_type == "simply_supported":
            Mu = (1.5 * (self.load * (self.span ** 2))) / 8  # kN-m
            Vu = (1.5 * (self.load * self.span) )/ 2  # kN
            delta_max = (5 * w * (L_mm ** 4)) / (384 * E * Ixx)  # mm
        elif self.beam_type == "cantilever":
            Mu = (1.5 * (self.load * (self.span ** 2))) / 2  # kN-m
            Vu = 1.5 * self.load * self.span  # kN (max at fixed end)
            delta_max = (w * (L_mm ** 4) )/ (8 * E * Ixx)  # mm
        else:
            return {"Error": "Unsupported beam type. Use 'simply_supported' or 'cantilever'."}

        bending_check = "Safe" if Md_kNm >= Mu else "Not Safe"

        # Shear checkself.
        Vd = (self.fy * tw * D) / (math.sqrt(3) * gamma_m0 * 1000)  # kN
        shear_check = "Safe" if Vu <= Vd else "Not Safe"

        # Deflection check
        if self.beam_type == "simply_supported":
            deflection_limit = (self.span * 1000) / 300  # mm
        elif self.beam_type == "cantilever":
            deflection_limit = (self.span * 1000) / 150  # mm
        deflection_check = "Safe" if delta_max <= deflection_limit else "Not Safe"



        # test
        mcr = self.calculate_Mcr(E, Iy, ry, D, tf)
        xlt = self.calculate_Xlt()

        result = {
            "section_name": self.section_name,
            "beam_type": self.beam_type.replace("_", " ").title(),
            "section_classification": section_class,
            "Design_Bending_Strength": round(Md_kNm, 2),
            "Maximum_Bending_Moment": round(Mu, 2),
            "Bending_Strength_Check": bending_check,
            "Shear_Force": round(Vu, 2),
            "Design_Shear_Capacity": round(Vd, 2),
            "Shear_Strength_Check": shear_check,
            "Maximum_Deflection": round(delta_max, 2),
            "Deflection_Limit": round(deflection_limit, 2),
            "Deflection_Check": deflection_check,
            "Critical_Moment": round(mcr/1e12, 2),
            "Xlt": round(xlt, 2),
            "span": self.span,
            "load": self.load,
            "fy": self.fy,
            "Llt": self.Llt,
            "alpha": self.alpha,
        }
        return result


def solve(request):
    if request.method == 'POST':
        span = float(request.POST.get('span'))
        load = float(request.POST.get('load'))
        fy = float(request.POST.get('fy'))
        section_name = request.POST.get('section_name')
        Llt = float(request.POST.get('Llt'))
        alpha = float(request.POST.get('alpha'))
        beam_type = request.POST.get('beam_type')

        unsupported = Unsupported(span, load, fy, section_name, Llt, alpha,beam_type)
        result = unsupported.design_laterally_unsupported_beam()

        return render(request, "unsupported.html", result)
    return render(request,"unsupported.html")