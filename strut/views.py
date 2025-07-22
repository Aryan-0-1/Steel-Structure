from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
import math

def main(request):
    return render(request,"strut.html")

class Strut:

    def __init__(self,fy,length,r_v,b1,b2,t,area,boundary_condition,k1,k2,k3,section_class,factored_load):
        self.fy = fy
        self.length = length
        self.r_v = r_v
        self.b1 = b1
        self.b2 =b2
        self.t = t
        self.area = area
        self.k = boundary_condition
        self.k1, self.k2, self.k3 = k1, k2, k3
        self.gamma_m0 = 1.1
        self.alpha = section_class
        self.factored_load = factored_load


    def slenderness_ratios(self):
        epsilon = math.sqrt(250 / self.fy)
        E = 2e5  # MPa
        lambda_vv = (self.length / self.r_v) / (epsilon * math.sqrt((math.pi ** 2 * E) / 250))
        lambda_phi = ((self.b1 + self.b2) / (2 * self.t)) / (epsilon * math.sqrt((math.pi ** 2 * E) / 250))
        return lambda_vv, lambda_phi


    def compressive_strength(self,lambda_e):
        phi = 0.5 * (1 + self.alpha * (lambda_e - 0.2) + lambda_e ** 2)
        return (self.fy / self.gamma_m0) / (phi + math.sqrt(phi ** 2 - lambda_e ** 2))


    def design_single_angle_strut(self):
        lambda_vv, lambda_phi = self.slenderness_ratios()
        lambda_e = math.sqrt(self.k1 + self.k2 * (lambda_vv ** 2) + self.k3 * (lambda_phi ** 2))

        fcd = self.compressive_strength(lambda_e)
        capacity = (fcd * self.area) / 1000  # in kN

        is_safe = self.factored_load <= capacity

        result = {'slenderness_ratio_vv': round(lambda_vv, 2),
                  'fy':self.fy,
                  "slenderness_ratio_phi": round(lambda_phi, 2),
                  "non_dimensional_slenderness_ratio": round(lambda_e, 2),
                  "compressive_strength": round(fcd, 2),
                  "load_carrying_capacity": round(capacity, 2),
                  "factored_load": round(self.factored_load, 2),
                  "is_load_safe": "Yes" if is_safe else "No",
                  "Boundary Condition": self.k,
                  'length': self.length,
                  'r_v': self.r_v,
                  'b1': self.b1,
                  'b2': self.b2,
                  't': self.t,
                  'area': self.area,
                  'k1': self.k1,
                  'k2': self.k2,
                  'k3': self.k3,
                  'section_class': self.alpha,
        }
        return result

def solve(request):
    if request.method == 'POST':
        fy =float(request.POST['fy'])
        length = float(request.POST['length'])
        r_v = float(request.POST['r_v'])
        b1 = float(request.POST['b1'])
        b2 = float(request.POST['b2'])
        t = float(request.POST['t'])
        area = float(request.POST['area'])
        boundary_condition = float(request.POST['boundary_condition'])
        section_class = float(request.POST['section_class'])
        factored_load = float(request.POST['factored_load'])
        k1 = float(request.POST['k1'])
        k2 = float(request.POST['k2'])
        k3 = float(request.POST['k3'])


        strut = Strut(fy,length,r_v,b1,b2,t,area,boundary_condition,k1,k2,k3,section_class,factored_load)
        result = strut.design_single_angle_strut()

        # return JsonResponse(result)
        return render(request, "strut.html", result)
    return render(request,"strut.html")
