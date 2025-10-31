from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
import math
import pandas as pd

def main(request):
    return render(request,"web.html")

class Web:

    def __init__(self,section_type,fy,alpha,applied_load,b):
        self.section_type = section_type
        self.fy = fy
        self.alpha = alpha
        self.applied_load = applied_load
        self.b = b

    def iscode(self):
        df = pd.read_csv(r'web\static\beams.csv')
        # section = self.section_type.str.split(' ')
        for i in range(len(df)):
            if df['Section '][i] == self.section_type:
                D = df['D(mm)'][i]
                tw = df['tw(mm)'][i]
                bf = df['bf(mm)'][i]
                tf = df['tf(mm)'][i]
                R = df['R(mm)'][i]
                return tw, D, bf, tf, R


    def web_buckling_strength(self,tw, D, bf, tf,R,gamma_m0=1.1):

        E = 2e5  # MPa
        epsilon = math.sqrt(250 / self.fy)
        dw = D - 2*(tf + R)
        if dw / tw < 67 * epsilon:
            return 0

        I = (dw * tw ** 3) / 12
        A = dw * tw
        r = math.sqrt(I / A)  # Radius of gyration about weak axis
        Le = 0.7 * dw
        lamda = Le / r

        lambda_e = (lamda / math.pi) * math.sqrt(self.fy / E)
        phi = 0.5 * (1 + self.alpha * (lambda_e - 0.2) + lambda_e ** 2)
        fcd = (self.fy / gamma_m0) / (phi + math.sqrt(phi * 2 - lambda_e * 2))

        n1 = D / 2
        Pbw = ((self.b + n1) * tw * fcd) / 1000  # kN
        return round(Pbw, 2)

    def web_crippling_strength(self, tw, bf, tf, R, gamma_m0=1.1):
        fyw = self.fy
        n2 = 2.5 * (tf + R)
        Pcw = ((self.b + n2) * tw * fyw) / (gamma_m0 * 1000)  # in kN
        return round(Pcw, 2)

    def check_web_local_failures(self):

        tw, D, bf, tf, R = self.iscode()
        buckling = self.web_buckling_strength( tw, D, bf, tf,R )
        crippling = self.web_crippling_strength( tw, bf, tf, R)
        factored_load = 1.5 * self.applied_load

        if buckling == 0:
            is_safe = factored_load <= crippling
        else:
            is_safe = factored_load <= buckling and factored_load <= crippling

        result =  {
            "section_type": self.section_type,
            "fy": self.fy,
            "alpha": self.alpha,
            "b": self.b,
            "applied_load": self.applied_load,
            "web_buckling_strength": buckling,
            "web_crippling_strength": crippling,
            "Applied Load (kN)": self.applied_load,
            "factored_load": round(factored_load, 2),
            "is_safe": "Yes" if is_safe else "No"
        }
        return result

def solve(request):
    if request.method == 'POST':
        section_type = request.POST['section_type']
        fy = float(request.POST['fy'])
        alpha = float(request.POST['alpha'])
        applied_load = float(request.POST['applied_load'])
        b = float(request.POST['b'])

        web = Web(section_type,fy,alpha,applied_load,b)
        result = web.check_web_local_failures()

        return render(request, "web.html", result)
    return render(request,"web.html")