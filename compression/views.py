from django.shortcuts import render
import math

def main(request):
    return render(request,"compression.html")


def solve(request):
    if request.method == 'POST':
        fy = float(request.POST.get('fy'))
        area = float(request.POST.get('area'))
        alpha = float(request.POST.get('alpha'))
        k = float(request.POST.get('k'))
        L = float(request.POST.get('L'))
        r = float(request.POST.get('r'))


        def get_design_compressive_strength(fy, area, alpha, k, L, r, gamma_m0=1.1):
            slenderness_ratio = (k * L) / r
            E = 2e5  # MPa

            # Euler buckling stress (critical stress)
            fcc = ((math.pi ** 2) * E) / (slenderness_ratio ** 2)  # Elastic buckling stress (MPa)

            # Buckling reduction factor (χ) as per IS 800:2007
            lambda_bar = math.sqrt(fy / fcc)
            phi = 0.5 * (1 + alpha * (lambda_bar - 0.2) + lambda_bar ** 2)
            chi = 1 / (phi + math.sqrt(phi ** 2 - lambda_bar ** 2))

            # Design compressive stress (fcd)
            fcd = (chi * fy) / gamma_m0

            # Design compressive strength (Pd = fcd * A)
            Pd = (fcd * area) / 1000  # Convert to kN
            ans = {'Pd':round(Pd,2)}
            result = {
                "fy": round(fy, 2),
                "area": round(area, 2),
                "alpha": round(alpha, 2),
                "k":k,
                "L":L,
                "r":r,
                "Pd": round(Pd, 2)

            }
            return result

        result = get_design_compressive_strength(fy, area, alpha, k, L, r)


        return render(request, "compression.html", result)
    return render(request,"compression.html")
