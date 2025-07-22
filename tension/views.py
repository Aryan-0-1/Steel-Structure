from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
import math

def main(request):
    return render(request,"tension.html")

class Tension:

    def __init__(self,fy,fu,L,w,n,d,do,t,Wc,g,alpha,section_type):
        self.fy = fy
        self.fu = fu
        self.L = L
        self.w = w
        self.n = n
        self.d = d
        self.do = do
        self.t = t
        self.Wc = Wc
        self.g = g
        self.alpha = alpha
        self.section_type = section_type


    def design_tension_member(self,gamma_m0=1.1, gamma_m1=1.25):
        # 1. Strength due to yielding of gross section
        Ag = self.Wc * self.t + (self.w - self.t) * self.t
        e = 1.5 * self.do
        p = 2.5 * self.d

        Tdg = (self.fy * Ag) / gamma_m0

        # 2. Strength due to rupture of net section
        if self.section_type == 'plate':
            An = (self.Wc - self.n * self.do) * self.t
            Tdn = (0.9 * An * self.fu) / gamma_m1

        elif self.section_type == 'angle':
            bs = self.w + p - self.t
            Lc = (self.n - 1) * p
            beta = 1.4 - 0.076 * (self.w / self.t) * (self.fy / self.fu) * (bs / Lc)
            beta = max(0.7, beta)
            Anc = (self.Wc - self.do - (self.t / 2)) * self.t
            Ago = (self.w - (self.t/2)) * self.t
            An = Anc + Ago

            # Effective net area for angle section
            Tdn1 = ((0.9 * Anc * self.fu) / gamma_m1) + ((beta * Ago * self.fy) / gamma_m0)

            Tdn2 = (self.alpha * An * self.fu) / gamma_m1
            Tdn = min(Tdn1, Tdn2)
        else:
            raise ValueError("Invalid section type. Choose 'plate' or 'angle'.")

        # 3. Strength due to block shear

        Avg = ((self.n - 1) * p + e) * self.t  # Gross shear area
        Avn = (e + ((self.n - 1) * p) - ((self.n * self.do) - (self.do / 2))) * self.t  # Net shear area
        Atg = p * self.t  # Gross tension area
        Atn = (p - (self.do / 2)) * self.t  # Net tension area

        Tdb1 = ((self.fy * Avg) / (math.sqrt(3) * gamma_m0)) + ((0.9 * self.fu * Atn) / gamma_m1)
        Tdb2 = ((0.9 * self.fu * Avn) / (math.sqrt(3) * gamma_m1) )+ ((self.fy * Atg) / gamma_m0)
        Tdb = min(Tdb1, Tdb2)

        # Final design strength is the minimum of these three
        design_strength = min(Tdg, Tdn, Tdb)

        return {
            "Tdg_Yield_Strength": round(Tdg/1000, 2),
            "Tdn_Rupture_Strength": round(Tdn/1000, 2),
            "Tdb_Block_Shear_Strength": round(Tdb/1000, 2),
            "Final_Design_Strength": round(design_strength/1000, 2),
            "fy":self.fy,
            "fu": self.fu,
            "L":self.L,
            "w" : self.w,
            "n" : self.n,
            "d" : self.d,
            "do" : self.do,
            "t" : self.t,
            "Wc" : self.Wc,
            "g" : self.g,
            "alpha" : self.alpha,
            "section_type" : self.section_type
        }



def solve(request):
    if request.method == 'POST':
        fy = float(request.POST.get('fy'))
        fu = float(request.POST.get('fu'))
        L = float(request.POST.get('L'))
        w = float(request.POST.get('w'))
        n = int(request.POST.get('n'))
        d = float(request.POST.get('d'))
        do = float(request.POST.get('do'))
        t = float(request.POST.get('t'))
        Wc = float(request.POST.get('Wc'))
        g = float(request.POST.get('g'))
        alpha = float(request.POST.get('alpha'))
        section_type = request.POST.get('section_type')


        tension = Tension(fy,fu,L,w,n,d,do,t,Wc,g,alpha,section_type)
        result = tension.design_tension_member()

        return render(request, "tension.html", result)
    return render(request,"tension.html")
