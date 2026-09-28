"""Design arithmetic for the 12 V -> 19 V boost converter (Samsung C27JG5x supply).

Every number the schematic and BOM use comes out of this file, so if a part
changes, change it here and re-run:

    python3 calc/boost_design.py

Controller is the SG3524 from the DTU shop, both output transistors paralleled
so the switch runs at the oscillator frequency. Voltage-mode control, type III
compensation around the SG3524's own error amplifier.
"""
import math
import numpy as np

# --------------------------------------------------------------------------
# Brief
# --------------------------------------------------------------------------
VIN_NOM, VIN_MIN, VIN_MAX = 12.0, 11.4, 12.6   # 12 V +-5 %
VOUT = 19.0
IOUT = 3.0                  # design load (monitor draws 2.53 A max)
IOUT_MIN = 0.1              # standby
ETA = 0.90                  # assumed, checked against the loss budget below

# --------------------------------------------------------------------------
# Chosen parts (all DTU shop unless noted)
# --------------------------------------------------------------------------
FSW = 100e3                 # switching frequency
L = 22e-6                   # hand-wound toroid (wire not from the shop)
R_L = 0.020                 # inductor DCR, estimate for ~1 mm2 copper
C_OUT_EACH, N_COUT, ESR_EACH = 1000e-6, 3, 0.060   # 1000 uF / 50 V electrolytic
VF_D = 0.85                 # BYW29-100 forward drop at ~3-6 A
RDS_ON = 0.040 * 1.5        # STP36NF06 40 mOhm max, x1.5 hot
QG = 30e-9                  # STP36NF06 total gate charge
R_SHUNT = 0.10 / 2          # 2 x 0R10 5 W in parallel, MOSFET source
V_CL = 0.200                # SG3524 current-limit threshold (CL+ - CL-)
VREF = 5.0                  # SG3524 reference, +-8 % worst case (4.6..5.4 V)
V_RAMP = 2.5                # SG3524 ramp swing at pin 9, ~1.0 .. 3.5 V

C_OUT = C_OUT_EACH * N_COUT
ESR = ESR_EACH / N_COUT


def hdr(t):
    print(f"\n=== {t} " + "=" * (70 - len(t)))


def eng(x, unit=""):
    for p, s in ((1e-12, "p"), (1e-9, "n"), (1e-6, "u"), (1e-3, "m"), (1, ""), (1e3, "k"), (1e6, "M")):
        if abs(x) < p * 1000:
            return f"{x / p:.3g} {s}{unit}"
    return f"{x:.3g} {unit}"


# --------------------------------------------------------------------------
# Steady state
# --------------------------------------------------------------------------
hdr("Operating point")
P_OUT = VOUT * IOUT
res = {}
for vin in (VIN_MIN, VIN_NOM, VIN_MAX):
    iin = P_OUT / ETA / vin
    # duty with diode drop and resistive loss in the input loop
    d = 1 - (vin - iin * (R_L + R_SHUNT + RDS_ON * 0.4)) / (VOUT + VF_D)
    di = vin * d / (FSW * L)
    ipk = iin + di / 2
    res[vin] = dict(iin=iin, d=d, di=di, ipk=ipk)
    print(f"Vin {vin:5.2f} V  Iin {iin:4.2f} A  D {d:.3f}  dI {di:4.2f} App  Ipk {ipk:4.2f} A")

w = res[VIN_MIN]            # worst case for current stress
n = res[VIN_NOM]
print(f"Pout {P_OUT:.1f} W; CCM/DCM boundary at Iout = {n['di'] / 2 * (1 - n['d']):.2f} A (standby runs DCM, fine)")

hdr("Inductor")
isat_req = w["ipk"] * 1.3
irms_l = math.sqrt(w["iin"] ** 2 + w["di"] ** 2 / 12)
energy = 0.5 * L * isat_req ** 2
print(f"L = {eng(L, 'H')}, ripple {n['di'] / n['iin'] * 100:.0f} % of Iin at 12 V")
print(f"needs Isat >= {isat_req:.1f} A (Ipk {w['ipk']:.2f} A x 1.3), Irms {irms_l:.2f} A")
print(f"stored energy at Isat: {energy * 1e3:.2f} mJ  -> powdered iron (-26/-52 mix) or gapped core, NOT plain ferrite")
wire_mm2 = irms_l / 5.0
print(f"copper for 5 A/mm2: {wire_mm2:.2f} mm2; skin depth {66 / math.sqrt(FSW):.2f} mm "
      f"-> 3 strands of 0.6-0.7 mm in parallel (or 2 x 0.9 mm)")
for al in (33, 46, 60, 75, 93):
    N = math.sqrt(L / (al * 1e-9))
    print(f"   if AL = {al:3d} nH/N^2 -> {N:4.1f} turns")

hdr("MOSFET (STP36NF06, 60 V / 36 A / 40 mOhm)")
irms_sw = w["iin"] * math.sqrt(w["d"])
p_cond = irms_sw ** 2 * RDS_ON
t_sw = 40e-9                 # rise + fall with the BD139/BD140 totem pole
p_sw = 0.5 * (VOUT + VF_D) * w["iin"] * t_sw * FSW
p_gate = QG * 10 * FSW
print(f"Vds stress {VOUT + VF_D:.1f} V + ringing (60 V part: 3x margin)")
print(f"Irms {irms_sw:.2f} A  Pcond {p_cond:.2f} W  Psw {p_sw:.2f} W  -> {p_cond + p_sw:.2f} W; gate drive {p_gate * 1e3:.0f} mW")

hdr("Diode (BYW29-100, 8 A / 100 V ultrafast)")
p_d = IOUT * VF_D
print(f"Iavg {IOUT:.1f} A, Ipk {w['ipk']:.1f} A, Vr {VOUT:.0f} V -> Pd {p_d:.2f} W -> TO-220 heatsink required")

hdr("Current sense / limit")
itrip = V_CL / R_SHUNT
p_shunt = irms_sw ** 2 * R_SHUNT
print(f"R_shunt {R_SHUNT * 1e3:.0f} mOhm  P {p_shunt:.2f} W")
# CL+ fed from shunt via divider Ra (top) / Rb (bottom) to trip at ~8.5 A
RA, RB = 1.0e3, 1.0e3
print(f"divider {RA / 1e3:.2f}k/{RB / 1e3:.2f}k: trip at {V_CL * (RA + RB) / RB / R_SHUNT:.1f} A peak "
      f"(nominal Ipk {n['ipk']:.1f} A, worst {w['ipk']:.1f} A)")

hdr("Output capacitor")
icout = IOUT * math.sqrt(w["d"] / (1 - w["d"]))
dv_c = IOUT * w["d"] / (FSW * C_OUT)
dv_esr = w["ipk"] * ESR
print(f"{N_COUT} x {eng(C_OUT_EACH, 'F')}: ripple current {icout:.2f} A total, {icout / N_COUT:.2f} A each")
print(f"ripple: {dv_c * 1e3:.1f} mV (charge) + {dv_esr * 1e3:.0f} mV (ESR {ESR * 1e3:.0f} mOhm) "
      f"= {(dv_c + dv_esr) / VOUT * 100:.2f} % of Vout")

hdr("Input capacitor")
icin = n["di"] / math.sqrt(12)
print(f"ripple current {icin:.2f} A rms -> 2 x 1000 uF / 50 V (0.3 A each)")

hdr("Loss budget")
p_l = irms_l ** 2 * R_L + 0.4          # + core loss estimate
p_ctrl = 12 * 0.015 + p_gate
p_caps = icout ** 2 * ESR
losses = dict(diode=p_d, mosfet=p_cond + p_sw, shunt=p_shunt, inductor=p_l, caps=p_caps, control=p_ctrl)
tot = sum(losses.values())
for k, v in losses.items():
    print(f"   {k:9s} {v:5.2f} W")
print(f"total {tot:.2f} W -> efficiency {P_OUT / (P_OUT + tot) * 100:.1f} % (assumed {ETA * 100:.0f} %)")

# --------------------------------------------------------------------------
# Oscillator
# --------------------------------------------------------------------------
hdr("Oscillator (SG3524: f = 1.30 / (RT CT))")
CT = 3.3e-9
RT = 1.30 / (FSW * CT)
RT_E96 = 3.92e3
print(f"CT {eng(CT, 'F')} -> RT {RT:.0f} Ohm -> {eng(RT_E96, 'Ohm')} gives {eng(1.3 / (RT_E96 * CT), 'Hz')} (+-10 %, trim not needed)")

# --------------------------------------------------------------------------
# Feedback divider and reference trim
# --------------------------------------------------------------------------
hdr("Feedback divider")
R_TOP, R_BOT = 205e3, 30.9e3
# IN+ from VREF through 9.09k / 2k trimmer / 9.09k. The trimmer has to span the
# SG3524's reference tolerance (4.6..5.4 V), not just resistor tolerance.
RR1, RPOT, RR2 = 9.09e3, 2e3, 9.09e3
G_DIV = 1 + R_TOP / R_BOT
for vref in (4.6, 5.0, 5.4):
    lo = vref * RR2 / (RR1 + RPOT + RR2) * G_DIV
    hi = vref * (RR2 + RPOT) / (RR1 + RPOT + RR2) * G_DIV
    ok = "reaches 19 V" if lo <= VOUT <= hi else "CANNOT reach 19 V"
    print(f"   Vref {vref:.1f} V: trimmer sets Vout {lo:5.2f} .. {hi:5.2f} V  ({ok})")
print(f"   trimmer centred: Vout {VREF * (RR2 + RPOT / 2) / (RR1 + RPOT + RR2) * G_DIV:.2f} V")

hdr("Over-voltage shutdown (SG3524 pin 10)")
VZ = 22.0   # BZX79C22
R_OV1, R_OV2 = 1e3, 4.75e3
v_trip = VZ + 0.7 * (1 + R_OV1 / R_OV2)
print(f"BZX79C22 + {R_OV1 / 1e3:.0f}k into SD, {R_OV2 / 1e3:.2f}k to GND: trips at ~{v_trip:.1f} V "
      f"({(VZ * 0.95 + 0.7 * 1.2):.1f}..{(VZ * 1.05 + 0.7 * 1.2):.1f} V over zener tolerance); 1.5KE24A TVS backs it up")

# --------------------------------------------------------------------------
# Loop: voltage-mode CCM boost + type III around the SG3524 error amp
# --------------------------------------------------------------------------
hdr("Compensation (type III)")
# The SG3524 error amp is a 2 mS transconductance stage that can only source
# ~200 uA into COMP (TI SLVS077: "any circuit that can sink 200 uA can pull COMP
# to ground").  Above fz2 an output step dV reaches IN- through R3 and needs
# dV/R3 from the amp, so R3 sets how big a disturbance stays linear.
R3, C3 = 5.23e3, 3.3e-9          # across R_TOP
RF, CF, CP = 13.0e3, 47e-9, 1e-9     # COMP -> IN-
A_EA, GBW_EA = 10 ** (80 / 20), 3e6
print(f"EA stays linear for output disturbances up to ~{200e-6 * R3:.2f} V (200 uA x R3)")

f = np.logspace(1, 5.5, 2000)
s = 2j * np.pi * f


def plant(vin, iout, esr=ESR, c=C_OUT):
    iin = VOUT * iout / ETA / vin
    d = 1 - (vin - iin * (R_L + R_SHUNT)) / (VOUT + VF_D)
    R = VOUT / iout
    Le = L / (1 - d) ** 2
    w0 = 1 / math.sqrt(Le * c)
    wrhp = (1 - d) ** 2 * R / L
    wesr = 1 / (esr * c)
    a1 = Le / R + c * (esr + R_L / (1 - d) ** 2)
    Gd0 = (VOUT + VF_D) / (1 - d)
    return Gd0 * (1 + s / wesr) * (1 - s / wrhp) / (1 + s * a1 + s ** 2 / w0 ** 2), w0 / 2 / math.pi, wrhp / 2 / math.pi


def comp():
    zin = 1 / (1 / R_TOP + 1 / (R3 + 1 / (s * C3)))
    zf = 1 / (1 / (RF + 1 / (s * CF)) + s * CP)
    a = A_EA / (1 + s * A_EA / (2 * np.pi * GBW_EA))
    # inverting amp with finite gain: Vc/Vo = -(zf/zin) / (1 + (1 + zf/zin)/a)
    return (zf / zin) / (1 + (1 + zf / zin) / a)


Gc = comp()
print(f"fz1 = {1 / (2 * math.pi * RF * CF):.0f} Hz, fz2 = {1 / (2 * math.pi * (R_TOP + R3) * C3):.0f} Hz, "
      f"fp1 = {1 / (2 * math.pi * R3 * C3) / 1e3:.1f} kHz, fp2 = {1 / (2 * math.pi * RF * CP) / 1e3:.1f} kHz")
print(f"{'case':34s} {'f0':>6s} {'fRHPZ':>7s} {'fc':>7s} {'PM':>6s} {'GM':>6s}")
worst_pm = 180
for vin in (VIN_MIN, VIN_NOM, VIN_MAX):
    for iout in (1.0, 2.0, 3.0):
        for esr_each in (0.03, 0.06, 0.15):
            Gp, f0, frhp = plant(vin, iout, esr=esr_each / N_COUT)
            T = Gc * Gp / V_RAMP
            mag = np.abs(T)
            ph = np.unwrap(np.angle(T)) * 180 / np.pi
            ic = np.where(np.diff(np.sign(mag - 1)))[0]
            fc = f[ic[-1]] if len(ic) else float("nan")
            pm = 180 + (ph[ic[-1]] - 360 * round((ph[ic[-1]]) / 360 - 0.5) - 180) if len(ic) else float("nan")
            pm = ((ph[ic[-1]] + 180) % 360) if len(ic) else float("nan")
            ig = np.where(np.diff(np.sign(((ph + 180) % 360) - 180)))[0]
            ig = [i for i in ig if f[i] > fc]
            gm = -20 * math.log10(mag[ig[0]]) if ig else float("inf")
            worst_pm = min(worst_pm, pm)
            print(f"Vin {vin:4.1f} Iout {iout:.0f} A ESR {esr_each * 1e3:3.0f} mOhm/cap "
                  f"{f0:6.0f} {frhp / 1e3:6.1f}k {fc / 1e3:6.2f}k {pm:5.0f}d {gm:5.1f}dB")
print(f"worst phase margin {worst_pm:.0f} deg")
