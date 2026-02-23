"""
5th Order vs 3rd Order PWM Filter - Frequency Response Comparison
================================================================
Computes analytical transfer functions for both filter designs
and generates Bode plots comparing frequency response and PWM attenuation.

Uses the standard Sallen-Key transfer function from TI SLOA024B:
  H(s) = 1 / (1 + s*C1*(R1+R2) + s²*R1*R2*C1*C2)
where C1 = shunt cap, C2 = feedback cap, R1/R2 = series resistors.

Combined with cascaded 1st order RC input stage.
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

# Output directory
OUT_DIR = Path(__file__).parent
IMG_DIR = Path(__file__).parent.parent.parent / 'Resources' / 'Pi Zero PWM Filter' / 'images'
IMG_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────
# Transfer function building blocks
# ─────────────────────────────────────────────────────────────

def rc_lowpass(f, R, C):
    """1st order RC low-pass: H(s) = 1 / (1 + s*R*C)"""
    s = 1j * 2 * np.pi * f
    return 1.0 / (1.0 + s * R * C)


def sallen_key_lp(f, R1, R2, C1, C2):
    """Unity-gain Sallen-Key 2nd order low-pass.

    From TI SLOA024B (K=1):
    H(s) = 1 / (1 + s*C1*(R1+R2) + s²*R1*R2*C1*C2)

    C1 = shunt cap (node between R1/R2 to GND)
    C2 = feedback cap (op-amp IN+ to OUT)
    """
    s = 1j * 2 * np.pi * f
    denom = 1.0 + s * C1 * (R1 + R2) + s**2 * R1 * R2 * C1 * C2
    return 1.0 / denom


def compute_filter_params(R1, R2, C1, C2):
    """Compute f0 and Q for a Sallen-Key stage."""
    f0 = 1.0 / (2 * np.pi * np.sqrt(R1 * R2 * C1 * C2))
    # From standard form: s² + (ω0/Q)s + ω0²
    # Comparing: ω0/Q = C1*(R1+R2) / (R1*R2*C1*C2) = (R1+R2)/(R1*R2*C2)
    omega0 = 2 * np.pi * f0
    omega0_over_Q = C1 * (R1 + R2) / (R1 * R2 * C1 * C2)
    Q = omega0 / omega0_over_Q
    return f0, Q


# ─────────────────────────────────────────────────────────────
# Filter definitions
# ─────────────────────────────────────────────────────────────

# Frequency sweep
f = np.logspace(1, 6, 2000)  # 10 Hz to 1 MHz, 2000 points

# ── 3rd Order: RC + Sallen-Key ──
# Input RC: R=2.2k, C=2.2nF
H_3_rc = rc_lowpass(f, 2200, 2.2e-9)
# Sallen-Key: R1=R2=1k, C1(shunt)=4.7nF, C2(fb)=10nF
H_3_sk = sallen_key_lp(f, 1000, 1000, 4.7e-9, 10e-9)
# Combined
H_3 = H_3_rc * H_3_sk

# ── 5th Order: RC + SK(Q=0.55) + SK(Q=1.29) ──
# Input RC: R=2.2k, C=1.5nF
H_5_rc = rc_lowpass(f, 2200, 1.5e-9)
# SK Stage 2: R=910, C1(shunt)=8.2nF, C2(fb)=10nF
H_5_sk1 = sallen_key_lp(f, 910, 910, 8.2e-9, 10e-9)
# SK Stage 3: R=2k, C1(shunt)=1.5nF, C2(fb)=10nF
H_5_sk2 = sallen_key_lp(f, 2000, 2000, 1.5e-9, 10e-9)
# Combined
H_5 = H_5_rc * H_5_sk1 * H_5_sk2

# Convert to dB and phase
gain_3 = 20 * np.log10(np.abs(H_3))
gain_5 = 20 * np.log10(np.abs(H_5))
phase_3 = np.angle(H_3, deg=True)
phase_5 = np.angle(H_5, deg=True)


# ─────────────────────────────────────────────────────────────
# Print stage parameters
# ─────────────────────────────────────────────────────────────

print("=" * 65)
print("PWM Filter Comparison: 3rd Order vs 5th Order")
print("Analytical Transfer Function Analysis")
print("=" * 65)

print("\n── 3rd Order Stage Parameters ──")
fc_rc = 1 / (2 * np.pi * 2200 * 2.2e-9)
print(f"  Input RC: fc = {fc_rc/1000:.1f} kHz")
f0, Q = compute_filter_params(1000, 1000, 4.7e-9, 10e-9)
print(f"  Sallen-Key: f0 = {f0/1000:.1f} kHz, Q = {Q:.2f}")

print("\n── 5th Order Stage Parameters ──")
fc_rc5 = 1 / (2 * np.pi * 2200 * 1.5e-9)
print(f"  Input RC: fc = {fc_rc5/1000:.1f} kHz")
f0_s2, Q_s2 = compute_filter_params(910, 910, 8.2e-9, 10e-9)
print(f"  SK Stage 2: f0 = {f0_s2/1000:.1f} kHz, Q = {Q_s2:.2f}")
f0_s3, Q_s3 = compute_filter_params(2000, 2000, 1.5e-9, 10e-9)
print(f"  SK Stage 3: f0 = {f0_s3/1000:.1f} kHz, Q = {Q_s3:.2f}")


# ─────────────────────────────────────────────────────────────
# Print key metrics
# ─────────────────────────────────────────────────────────────

def find_3db(f, gain_db):
    """Find -3dB frequency."""
    idx = np.where(gain_db <= gain_db[0] - 3)[0]
    return f[idx[0]] if len(idx) > 0 else 0

def atten_at(f, gain_db, freq_target):
    """Attenuation at a target frequency."""
    idx = np.argmin(np.abs(f - freq_target))
    return gain_db[idx]

print("\n── AC Analysis Results ──")
fc3 = find_3db(f, gain_3)
fc5 = find_3db(f, gain_5)
print(f"  3rd Order: -3dB cutoff = {fc3/1000:.1f} kHz")
print(f"  5th Order: -3dB cutoff = {fc5/1000:.1f} kHz")

for freq_t, label in [(31250, '31.25 kHz (PWM)'), (62500, '62.5 kHz (2nd)'), (93750, '93.75 kHz (3rd)')]:
    a3 = atten_at(f, gain_3, freq_t)
    a5 = atten_at(f, gain_5, freq_t)
    print(f"  @ {label}: 3rd = {a3:.1f} dB, 5th = {a5:.1f} dB")

# Approximate roll-off rate
for gain, label in [(gain_3, '3rd'), (gain_5, '5th')]:
    i_lo = np.argmin(np.abs(f - 50000))
    i_hi = np.argmin(np.abs(f - 500000))
    slope = (gain[i_hi] - gain[i_lo]) / np.log10(f[i_hi] / f[i_lo])
    print(f"  {label} Order roll-off: {slope:.0f} dB/decade")


# ─────────────────────────────────────────────────────────────
# Plot 1: Full Bode Plot Comparison
# ─────────────────────────────────────────────────────────────

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
fig.suptitle('PWM Filter Comparison: 3rd Order vs 5th Order\n'
             'Analytical Bode Plot (Magnitude & Phase)',
             fontsize=14, fontweight='bold')

# Magnitude
ax1.semilogx(f, gain_3, 'b-', linewidth=2, label='3rd Order (RC + SK)')
ax1.semilogx(f, gain_5, 'r-', linewidth=2, label='5th Order (RC + 2×SK)')

# Mark PWM frequency and harmonics
for freq_mark, style in [(31250, '--'), (62500, ':'), (93750, ':')]:
    ax1.axvline(x=freq_mark, color='gray', linestyle=style, alpha=0.5)
ax1.axhline(y=-3, color='green', linestyle=':', alpha=0.5)

# Annotate attenuation at PWM freq
a3_pwm = atten_at(f, gain_3, 31250)
a5_pwm = atten_at(f, gain_5, 31250)
ax1.plot(31250, a3_pwm, 'bo', markersize=10, zorder=5)
ax1.plot(31250, a5_pwm, 'ro', markersize=10, zorder=5)
ax1.annotate(f'{a3_pwm:.1f} dB', xy=(31250, a3_pwm),
             xytext=(55000, a3_pwm + 8), fontsize=11, color='blue',
             fontweight='bold', arrowprops=dict(arrowstyle='->', color='blue'))
ax1.annotate(f'{a5_pwm:.1f} dB', xy=(31250, a5_pwm),
             xytext=(55000, a5_pwm + 8), fontsize=11, color='red',
             fontweight='bold', arrowprops=dict(arrowstyle='->', color='red'))

# Labels
ax1.text(31250, 5, '31.25 kHz\n(PWM)', ha='center', fontsize=9, color='gray')
ax1.set_ylabel('Gain (dB)', fontsize=12)
ax1.set_ylim(-140, 15)
ax1.legend(loc='lower left', fontsize=11)
ax1.grid(True, which='both', alpha=0.3)

# Phase
ax2.semilogx(f, phase_3, 'b-', linewidth=2, label='3rd Order')
ax2.semilogx(f, phase_5, 'r-', linewidth=2, label='5th Order')
ax2.axvline(x=31250, color='gray', linestyle='--', alpha=0.5)

ax2.set_ylabel('Phase (degrees)', fontsize=12)
ax2.set_xlabel('Frequency (Hz)', fontsize=12)
ax2.legend(loc='lower left', fontsize=11)
ax2.grid(True, which='both', alpha=0.3)

plt.tight_layout()
plt.savefig(OUT_DIR / 'filter_comparison_bode.png', dpi=150, bbox_inches='tight')
plt.savefig(IMG_DIR / 'filter_comparison_bode.png', dpi=150, bbox_inches='tight')
print(f"\nSaved: filter_comparison_bode.png")


# ─────────────────────────────────────────────────────────────
# Plot 2: Audio Band Detail (20 Hz - 20 kHz)
# ─────────────────────────────────────────────────────────────

fig2, ax3 = plt.subplots(1, 1, figsize=(12, 5))
fig2.suptitle('Audio Band Passband Detail (20 Hz - 20 kHz)',
              fontsize=14, fontweight='bold')

mask = (f >= 20) & (f <= 25000)
ax3.semilogx(f[mask], gain_3[mask], 'b-', linewidth=2, label='3rd Order')
ax3.semilogx(f[mask], gain_5[mask], 'r-', linewidth=2, label='5th Order')
ax3.axhline(y=-3, color='green', linestyle=':', alpha=0.5, label='-3 dB')
ax3.axhline(y=-1, color='orange', linestyle=':', alpha=0.3)
ax3.axhline(y=1, color='orange', linestyle=':', alpha=0.3)
ax3.fill_between([20, 25000], -1, 1, alpha=0.05, color='orange', label='±1 dB band')

ax3.set_ylabel('Gain (dB)', fontsize=12)
ax3.set_xlabel('Frequency (Hz)', fontsize=12)
ax3.set_ylim(-10, 5)
ax3.legend(fontsize=10)
ax3.grid(True, which='both', alpha=0.3)

plt.tight_layout()
plt.savefig(OUT_DIR / 'filter_comparison_audioband.png', dpi=150, bbox_inches='tight')
plt.savefig(IMG_DIR / 'filter_comparison_audioband.png', dpi=150, bbox_inches='tight')
print(f"Saved: filter_comparison_audioband.png")


# ─────────────────────────────────────────────────────────────
# Plot 3: Individual Stage Contributions (5th order)
# ─────────────────────────────────────────────────────────────

fig3, ax4 = plt.subplots(1, 1, figsize=(12, 6))
fig3.suptitle('5th Order Filter — Individual Stage Contributions',
              fontsize=14, fontweight='bold')

gain_5_rc = 20 * np.log10(np.abs(H_5_rc))
gain_5_sk1 = 20 * np.log10(np.abs(H_5_sk1))
gain_5_sk2 = 20 * np.log10(np.abs(H_5_sk2))

ax4.semilogx(f, gain_5_rc, 'g--', linewidth=1.5, label=f'RC input (fc={fc_rc5/1000:.0f} kHz)')
ax4.semilogx(f, gain_5_sk1, 'c--', linewidth=1.5, label=f'SK Stage 2 Q={Q_s2:.2f} (f₀={f0_s2/1000:.0f} kHz)')
ax4.semilogx(f, gain_5_sk2, 'm--', linewidth=1.5, label=f'SK Stage 3 Q={Q_s3:.2f} (f₀={f0_s3/1000:.0f} kHz)')
ax4.semilogx(f, gain_5, 'r-', linewidth=2.5, label='Combined 5th Order')

ax4.axvline(x=31250, color='gray', linestyle='--', alpha=0.5)
ax4.text(31250, 5, 'PWM 31.25 kHz', ha='center', fontsize=9, color='gray')
ax4.axhline(y=-3, color='green', linestyle=':', alpha=0.4)

ax4.set_ylabel('Gain (dB)', fontsize=12)
ax4.set_xlabel('Frequency (Hz)', fontsize=12)
ax4.set_ylim(-120, 15)
ax4.legend(loc='lower left', fontsize=10)
ax4.grid(True, which='both', alpha=0.3)

plt.tight_layout()
plt.savefig(OUT_DIR / 'filter_5th_order_stages.png', dpi=150, bbox_inches='tight')
plt.savefig(IMG_DIR / 'filter_5th_order_stages.png', dpi=150, bbox_inches='tight')
print(f"Saved: filter_5th_order_stages.png")


# ─────────────────────────────────────────────────────────────
# Summary Table
# ─────────────────────────────────────────────────────────────

print("\n" + "=" * 65)
print("COMPARISON SUMMARY")
print("=" * 65)
print(f"{'Metric':<40} {'3rd Order':>11} {'5th Order':>11}")
print("-" * 65)
print(f"{'Cutoff frequency (-3dB)':<40} {fc3/1000:>9.1f} kHz {fc5/1000:>9.1f} kHz")

for freq_t, label in [(31250, '31.25 kHz (PWM fundamental)'),
                       (62500, '62.5 kHz (2nd harmonic)'),
                       (93750, '93.75 kHz (3rd harmonic)')]:
    a3 = atten_at(f, gain_3, freq_t)
    a5 = atten_at(f, gain_5, freq_t)
    print(f"{'Attenuation @ ' + label:<40} {a3:>9.1f} dB  {a5:>9.1f} dB")

# Roll-off
for gain, label in [(gain_3, '3rd Order'), (gain_5, '5th Order')]:
    i_lo = np.argmin(np.abs(f - 50000))
    i_hi = np.argmin(np.abs(f - 500000))
    slope = (gain[i_hi] - gain[i_lo]) / np.log10(f[i_hi] / f[i_lo])
    print(f"{'Roll-off (' + label + ')':<40} {slope:>8.0f} dB/dec")

improvement = atten_at(f, gain_5, 31250) - atten_at(f, gain_3, 31250)
print(f"\n{'5th order improvement @ PWM freq':<40} {improvement:>9.1f} dB")
print("=" * 65)
