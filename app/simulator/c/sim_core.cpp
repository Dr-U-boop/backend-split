#include <math.h>
#include <stddef.h>
#include <vector>

#include "third_party/lsoda.hpp"

#define MODEL_SIBR 1
#define MODEL_DM 2

static double H(double x) {
    return x > 0.0 ? 1.0 : 0.0;
}

static double clamp_exp_arg(double x) {
    if (x < -709.0) return -709.0;
    if (x > 709.0) return 709.0;
    return x;
}

static void control_alg(
    double t,
    double tms,
    const double* scen,
    double* vbas,
    double* vbol,
    double* vm,
    double* Dig
) {
    const double M = scen[0];
    const double tm = scen[1];
    const double Tm = scen[2] > 0.0 ? scen[2] : 1.0;
    const double ti_1 = scen[7];
    const double ti_2 = scen[8];
    const double Ti_1 = scen[9] > 0.0 ? scen[9] : 1.0;
    const double Ti_2 = scen[10] > 0.0 ? scen[10] : 1.0;
    const double Dbol_1 = scen[13];
    const double Dbol_2 = scen[14];
    const double Vbas = scen[15];

    *vbas = Vbas * 6000.0 / 60.0;

    const double bol1 = (1.0 / Ti_1) * Dbol_1
        * (1.0 / (1.0 + exp(clamp_exp_arg(-3.0 * (t + 10.0 - ti_1)))))
        * (1.0 / (1.0 + exp(clamp_exp_arg(-3.0 * (-10.0 + ti_1 - t + Ti_1)))));

    const double bol2 = (1.0 / Ti_2) * Dbol_2
        * (1.0 / (1.0 + exp(clamp_exp_arg(-3.0 * (t + 10.0 - ti_2)))))
        * (1.0 / (1.0 + exp(clamp_exp_arg(-3.0 * (-10.0 + ti_2 - t + Ti_2)))));

    *vbol = 6000.0 * (bol1 + bol2);
    *Dig = 1176.0 * M;
    *vm = (*Dig / Tm) * H(t - tm - tms) * H(-(t - tm - Tm - tms));
}

static void deriv_sibr(
    const double* y,
    double* dy,
    double t,
    const double* p,
    const double* scen,
    double tms
) {
    const double gp = y[0], Il = y[1], Ip = y[2], fgut = y[3], fliq = y[4], fsol = y[5], gt = y[6], Xt = y[7],
                 Ii = y[8], It = y[9], Hp = y[10], SRsh = y[11], gl = y[12], Phn1 = y[13], Pha1 = y[14],
                 Phn2 = y[15], Pha2 = y[16], yg = y[17], PCa = y[18], PCn = y[19], pyr = y[20], Er = y[21], Er1 = y[22];

    const double mt = p[0], Vi = p[1], ki1 = p[2], ki2 = p[3], ki3 = p[4], kgabs = p[5], kgri = p[6],
                 kmin = p[7], kmax = p[8], k1gg = p[9], k2gg = p[10], ucns = p[11], vidb = p[12], kres = p[13],
                 k1e = p[14], k2e = p[15], k1abs = p[16], k2abs = p[17], ks = p[18], kd = p[19], ksen = p[20],
                 lbh = p[21], gth = p[22], kh1 = p[23], kh2 = p[24], kh3 = p[25], kh4 = p[26], k1gl = p[27],
                 k2gl = p[28], kh5 = p[29], kh6 = p[30], k1gng = p[31], k2gng = p[32], kKc = p[33], ib = p[34],
                 gb = p[35], kret = p[36], kdec = p[37], delth_g = p[38], vid = p[39], Kidb = p[40], vgg = p[41],
                 vgl = p[42], Kgl = p[43], Kgn = p[44], Ki = p[45], vgng = p[46], Kgng = p[47], k1i = p[48],
                 k2i = p[49], k3i = p[50], di = p[51], dh = p[52];

    double vbas, vbol, vm, Dig;
    control_alg(t, tms, scen, &vbas, &vbol, &vm, &Dig);

    double dfgut = 0.0, dfliq = 0.0, dfsol = 0.0;
    double dgp = 0.0, dgl = 0.0, dgt = 0.0, dXt = 0.0, dIl = 0.0, dIp = 0.0;
    double dSRsh = 0.0, dIi = 0.0, dIt = 0.0, dHp = 0.0;
    double dPhn1 = 0.0, dPha1 = 0.0, dPhn2 = 0.0, dPha2 = 0.0, dyg = 0.0;
    double dPCa = 0.0, dPCn = 0.0, dpyr = 0.0, dEr = 0.0, dEr1 = 0.0;

    const double safeDig = Dig > 1e-12 ? Dig : 1e-12;
    const double safe1mkdec = fabs(1.0 - kdec) > 1e-12 ? (1.0 - kdec) : 1e-12;
    const double saferet = fabs(kret) > 1e-12 ? kret : 1e-12;

    const double alp = 5.0 / (2.0 * safeDig * safe1mkdec);
    const double bet = 5.0 / (2.0 * safeDig * saferet);

    const double kgut = kmin + (kmax - kmin) / 2.0 * (
        tanh(alp * (fsol + fliq - kdec * safeDig)) - tanh(bet * (fsol + fliq - kret * safeDig)) + 2.0
    );

    const double fmeal = delth_g / mt * kgabs * fgut;
    const double eren = k1e * (gp - k2e) * H(gp - k2e);

    const double Vmx = vidb + vid * Xt;
    const double Uid = (Vmx * gt) / (Kidb + gt);

    const double Nyp = 400.0;
    const double Kyp = 200.0;
    const double yp = Nyp * yg / (Kyp + yg);

    const double vgg_1 = (vgg * Pha2 * gl) / (Kgn + gl);
    const double vgl_1 = (vgl * Pha1 * yp) / ((1.0 + (Il / Ki)) * (Kgl + yp));
    const double vgng_1 = (vgng * PCa * Er1) / (Kgng + Er1);

    dgp = fmeal - eren - ucns - k1gg * gp + k2gg * gt - gp * k1gl + gl * k2gl;
    dgl = gp * k1gl - gl * k2gl + vgl_1 - vgg_1 + vgng_1;
    dgt = -Uid + k1gg * gp - k2gg * gt;
    dXt = -kres * Xt + kres * ((Ip / Vi) - ib) * H((Ip / Vi) - ib);
    dIl = -(k1i + k3i) * Il + k2i * Ip;
    dIp = -k2i * Ip + k1i * Il + k2abs / mt * It - di * Ip;
    dfgut = -kgabs * fgut + kgut * fliq;
    dfliq = -kgut * fliq + kgri * fsol;
    dfsol = -kgri * fsol + vm;

    const double SRdh = kd * (-dgp) * H(-dgp);

    dSRsh = (-ks * (SRsh - lbh)) * H(gp - gb)
        + (-ks * (SRsh - (ksen * ((gth - gp) * H(gth - gp) / (Ip + 1.0)) + lbh) * H(ksen * (gth - gp) / (Ip + 1.0) + lbh)))
            * H(gb - gp);

    dIi = -k1abs * Ii + vbas + vbol;
    dIt = k1abs * Ii - k2abs * It;
    dHp = -dh * Hp + SRsh + SRdh;
    dPhn1 = kh3 * Il * Pha1 - kh4 * Phn1 * Hp;
    dPha1 = -kh3 * Il * Pha1 + kh4 * Phn1 * Hp;
    dPhn2 = kh2 * Pha2 * Hp - kh1 * Il * Phn2;
    dPha2 = kh1 * Il * Phn2 - kh2 * Pha2 * Hp;
    dyg = vgg_1 - vgl_1;
    dPCa = kh5 * Hp * PCn - kh6 * PCa * Il;
    dPCn = -kh5 * Hp * PCn + kh6 * PCa * Il;
    dpyr = Uid - k1gng * pyr - kKc * pyr;
    dEr = k1gng * pyr - k2gng * Er;
    dEr1 = k2gng * Er - vgng_1;

    dy[0] = dgp;
    dy[1] = dIl;
    dy[2] = dIp;
    dy[3] = dfgut;
    dy[4] = dfliq;
    dy[5] = dfsol;
    dy[6] = dgt;
    dy[7] = dXt;
    dy[8] = dIi;
    dy[9] = dIt;
    dy[10] = dHp;
    dy[11] = dSRsh;
    dy[12] = dgl;
    dy[13] = dPhn1;
    dy[14] = dPha1;
    dy[15] = dPhn2;
    dy[16] = dPha2;
    dy[17] = dyg;
    dy[18] = dPCa;
    dy[19] = dPCn;
    dy[20] = dpyr;
    dy[21] = dEr;
    dy[22] = dEr1;
}

static void deriv_dm(
    const double* y,
    double* dy,
    double t,
    const double* scen,
    double tms
) {
    const double gp = y[0], Il = y[1], Ip = y[2], fgut = y[3], fliq = y[4], fsol = y[5],
                 gt = y[6], I1 = y[7], Id = y[8], Xt = y[9], Ipo = y[10], Yt = y[11], Ii = y[12], It = y[13];

    double vbas, vbol, vm, Dig;
    control_alg(t, tms, scen, &vbas, &vbol, &vm, &Dig);

    double k[38] = {0.0};
    k[1] = 79.7963;
    k[2] = 104.08;
    k[3] = 122.4;
    k[4] = 1.55;
    k[5] = 0.05;
    k[6] = 0.190;
    k[7] = 0.27;
    k[8] = 0.3484;
    k[9] = 2.97e-2;
    k[10] = 12e-2;
    k[11] = 11.3e-3;
    k[12] = 2.76;
    k[13] = 0.0021;
    k[14] = 0.009;
    k[15] = 0.0618;
    k[16] = 0.0079;
    k[17] = 0.9;
    k[18] = 0.057;
    k[19] = 0.056;
    k[20] = 0.008;
    k[21] = 0.056;
    k[22] = 0.68;
    k[23] = 0.13;
    k[24] = 1.8;
    k[25] = 0.065;
    k[26] = 0.079;
    k[27] = 0.25;
    k[28] = 2.0;
    k[29] = 0.087;
    k[30] = 205.59;
    k[31] = 0.0731;
    k[32] = 0.0005;
    k[33] = 339.0 / k[24];
    k[34] = 0.5;
    k[35] = 0.050;
    k[36] = 0.11;

    const double EGP = (k[12] - k[13] * gp - k[14] * Id - k[15] * Ipo) * H(k[12] - k[13] * gp - k[14] * Id - k[15] * Ipo);

    const double safeDig = Dig > 1e-12 ? Dig : 1e-12;
    const double c1 = fabs(1.0 - k[22]) > 1e-12 ? (1.0 - k[22]) : 1e-12;
    const double c2 = fabs(k[23]) > 1e-12 ? k[23] : 1e-12;

    const double kgut = k[20] + (k[21] - k[20]) / 2.0
        * (tanh((5.0 / (2.0 * safeDig * c1)) * (fsol + fliq - k[22] * safeDig))
            - tanh((5.0 / (2.0 * safeDig * c2)) * (fsol + fliq - k[23] * safeDig)) + 2.0);

    dy[0] = EGP + k[17] / k[1] * k[18] * fgut - k[27] - k[32] * (gp - k[33]) * H(gp - k[33]) - k[25] * gp + k[26] * gt;
    dy[6] = -((k[28] + k[29] * Xt) * gt) / (k[30] + gt) + k[25] * gp - k[26] * gt;
    dy[7] = -k[16] * (I1 - Ip / k[5]);
    dy[8] = -k[16] * (Id - I1);
    dy[9] = -k[31] * Xt + k[31] * ((Ip / k[5]) - k[2]) * H((Ip / k[5]) - k[2]);
    dy[1] = -(k[6] + k[8]) * Il + k[7] * Ip;
    dy[2] = -k[7] * Ip + k[6] * Il + k[11] / k[1] * It - k[10] * Ip;
    dy[3] = -k[18] * fgut + kgut * fliq;
    dy[4] = -kgut * fliq + k[19] * fsol;
    dy[5] = -k[19] * fsol + vm;
    dy[10] = -k[34] * Ipo + (Yt + k[4]) * H(dy[0]) + (Yt + k[4]) * H(-dy[0]);
    dy[11] = -k[35] * (Yt - k[36] * (gp / k[24] - k[3])) * H(k[36] * (gp / k[24] - k[3]) + k[4])
        + (-k[35] * Yt - k[35] * k[4]) * H(-k[4] - k[36] * (gp / k[24] - k[3]));
    dy[13] = k[9] * Ii - k[11] * It;
    dy[12] = -k[9] * Ii + vbas + vbol;
}

static void rk4_step_sibr(double* y, int n, double t, double dt, const double* p, const double* scen, double tms) {
    double k1[32] = {0.0}, k2[32] = {0.0}, k3[32] = {0.0}, k4[32] = {0.0}, yt[32] = {0.0};

    deriv_sibr(y, k1, t, p, scen, tms);
    for (int i = 0; i < n; i++) yt[i] = y[i] + 0.5 * dt * k1[i];

    deriv_sibr(yt, k2, t + 0.5 * dt, p, scen, tms);
    for (int i = 0; i < n; i++) yt[i] = y[i] + 0.5 * dt * k2[i];

    deriv_sibr(yt, k3, t + 0.5 * dt, p, scen, tms);
    for (int i = 0; i < n; i++) yt[i] = y[i] + dt * k3[i];

    deriv_sibr(yt, k4, t + dt, p, scen, tms);
    for (int i = 0; i < n; i++) {
        y[i] += (dt / 6.0) * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i]);
    }
}

static void rk4_step_dm(double* y, int n, double t, double dt, const double* scen, double tms) {
    double k1[32] = {0.0}, k2[32] = {0.0}, k3[32] = {0.0}, k4[32] = {0.0}, yt[32] = {0.0};

    deriv_dm(y, k1, t, scen, tms);
    for (int i = 0; i < n; i++) yt[i] = y[i] + 0.5 * dt * k1[i];

    deriv_dm(yt, k2, t + 0.5 * dt, scen, tms);
    for (int i = 0; i < n; i++) yt[i] = y[i] + 0.5 * dt * k2[i];

    deriv_dm(yt, k3, t + 0.5 * dt, scen, tms);
    for (int i = 0; i < n; i++) yt[i] = y[i] + dt * k3[i];

    deriv_dm(yt, k4, t + dt, scen, tms);
    for (int i = 0; i < n; i++) {
        y[i] += (dt / 6.0) * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i]);
    }
}

typedef struct {
    int model_type;
    const double* patient;
    const double* scenario;
    double tms;
} lsoda_context_t;

static void rhs_sibr_lsoda(double t, double* y, double* dydt, void* data) {
    const lsoda_context_t* ctx = (const lsoda_context_t*)data;
    deriv_sibr(y, dydt, t, ctx->patient, ctx->scenario, ctx->tms);
}

static void rhs_dm_lsoda(double t, double* y, double* dydt, void* data) {
    const lsoda_context_t* ctx = (const lsoda_context_t*)data;
    deriv_dm(y, dydt, t, ctx->scenario, ctx->tms);
}

extern "C" int run_simulation_model(
    int model_type,
    const double* patient,
    int patient_len,
    const double* init_state,
    int init_len,
    const double* scenario,
    int scenario_len,
    double t0,
    double dt,
    int steps,
    double tms,
    double* out_time,
    double* out_glucose
) {
    if (!patient || !init_state || !scenario || !out_time || !out_glucose) return -1;
    if (patient_len < 53 || scenario_len < 16 || dt <= 0.0 || steps <= 1) return -2;

    int n = 0;
    if (model_type == MODEL_SIBR) n = 23;
    else if (model_type == MODEL_DM) n = 14;
    else return -3;

    if (init_len < n) return -4;

    std::vector<double> y((size_t)n, 0.0);
    std::vector<double> yout((size_t)n, 0.0);
    for (int i = 0; i < n; i++) y[(size_t)i] = init_state[i];

    LSODA::LSODA solver;
    lsoda_context_t ctx = {
        model_type,
        patient,
        scenario,
        tms,
    };
    LSODA::LSODA_ODE_SYSTEM_TYPE rhs = (model_type == MODEL_SIBR) ? rhs_sibr_lsoda : rhs_dm_lsoda;

    double t = t0;
    int istate = 1;
    out_time[0] = t;
    out_glucose[0] = y[0];

    try {
        for (int i = 1; i < steps; i++) {
            const double tout = t0 + i * dt;
            solver.lsoda_function(rhs, (size_t)n, y, yout, &t, tout, &istate, &ctx, 1e-8, 1e-8);
            if (istate < 0) return -20;

            y = yout;
            if (!isfinite(y[0])) return -10;
            if (y[0] < 0.0) y[0] = 0.0;
            if (y[0] > 2000.0) y[0] = 2000.0;

            out_time[i] = t;
            out_glucose[i] = y[0];
        }
    } catch (...) {
        return -30;
    }

    return 0;
}
