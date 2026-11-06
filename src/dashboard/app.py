"""Fraud Watch - the fraud officer's shift screen.
Replays the labeled 17-day future window using the Phase-4 GBT-d5 scores read
offline from CSV; no Spark in the UI. The science lives in the Statistics tab."""
import time
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CSV, THR, TICK = "data/processed/dashboard_test.csv", 0.5, 0.25
TOP = [("V258", 5.5), ("C13", 4.6), ("C1", 4.4), ("TransactionAmt", 4.1), ("card1_amt_avg", 4.0),
       ("C14", 3.9), ("C11", 3.5), ("day", 3.0), ("card6_idx", 2.6), ("card3", 2.6)]


def cm(d, t):
    """the single metric ruler: confusion + ranking for score column p_gbt at threshold t"""
    p, y = d["p_gbt"] >= t, d["isFraud"] == 1
    tp, fp, fn, tn = int((p & y).sum()), int((p & ~y).sum()), int((~p & y).sum()), int((~p & ~y).sum())
    pr, rc = tp / (tp + fp) if tp + fp else 0.0, tp / (tp + fn) if tp + fn else 0.0
    return tp, fp, fn, tn, pr, rc, 2 * pr * rc / (pr + rc) if pr + rc else 0.0


def risk(p):
    return ("red", "HIGH") if p >= 0.7 else (("orange", "MEDIUM") if p >= 0.4 else ("green", "low"))


def card_tag(v):
    return "card ..." + f"{int(v) % 1000:03d}"


def size_note(a):
    return "tiny for this card" if a < 0.5 else (f"{a:.1f}x the card's usual spend" if a > 3 else "usual size for this card")


def band(d, t):
    tp, fp, fn, _, pr, rc, f1 = cm(d, t)
    money = d.loc[(d["isFraud"] == 1) & (d["p_gbt"] >= t), "TransactionAmt"].sum()
    c = st.columns(6)
    c[0].metric("alarms raised", f"{tp + fp:,}")
    c[1].metric("real fraud caught", f"{tp:,}", f"{fn:,} missed")
    c[2].metric("predictive money at risk", f"${money:,.0f}")
    c[3].metric("alarm accuracy", f"{pr:.3f}", f"{fp:,} false alarms")
    c[4].metric("fraud found", f"{rc:.0%}")
    c[5].metric("balance score (F1)", f"{f1:.3f}")


st.set_page_config(page_title="Fraud Watch", layout="wide")
try:
    @st.cache_data
    def load():
        d = pd.read_csv(CSV)
        d["isFraud"] = d["isFraud"].astype(int)
        return d
    df = load()
except FileNotFoundError:
    st.error(f"{CSV} missing - run Cell 17 of 06_full_scale_training.ipynb first.")
    st.stop()

@st.cache_data
def qband(col):
    return np.quantile(df[col], np.linspace(0, 1, 101))


def reasons(r):
    out = []
    a, n = r["amt_vs_card"], int(r["card1_txn_24h"])
    if a < 0.5:
        out.append(f"This charge is only {a:.0%} of the card's usual spend - a classic card-testing move")
    elif a > 3:
        out.append(f"The charge is {a:.1f}x the card's usual spend - well outside this card's habits")
    if n >= 5:
        out.append(f"The card has made {n} charges in the last 24 hours - unusually busy today")
    if r["TransactionAmt"] < 10 and n > 3:
        out.append("A burst of small charges - the stolen-card testing signature from the Phase-2 analysis")
    pos = np.searchsorted(qband("V258"), r["V258"]) / 100
    if pos >= 0.95 or pos <= 0.05:
        out.append(f"It fires an anonymized risk pattern at the extreme of the dataset (top {max(pos, 1 - pos):.0%})")
    return out[:3] or ["No single signal shouts - the model flags the overall combination"]


N, F = len(df), int(df["isFraud"].sum())
START = int(df.index[df["p_gbt"] >= THR][0])     # the shift opens on the first alert - never dead
ss = st.session_state
ss.setdefault("cursor", START)
ss.setdefault("playing", True)
ss.setdefault("verdicts", {})                    # case id -> "confirmed" | "dismissed"

with st.sidebar:
    st.title("Fraud Watch")
    st.caption(f"Replay of the labeled future window (days 166-182), verdicts from the Phase-4 model read offline. "
               f"{N:,} transactions | {F:,} real fraud. No Spark in the UI.")
    mode = st.radio("View", ["Shift screen", "Statistics"], key="mode")
    speed = st.slider("Replay speed (x)", 1, 10, 3, disabled=mode != "Shift screen")

if mode == "Shift screen":
    w = df.iloc[: ss.cursor]                     # transactions seen so far
    day = int(w.iloc[-1]["day"])

    st.progress(ss.cursor / N, text=f"shift progress - day {day} of 183 (replaying future days 166-182)")
    c1, c2, _ = st.columns([1, 1, 8])
    if c1.button("Play/Pause"):
        ss.playing = not ss.playing
    if c2.button("Reset shift"):
        ss.cursor, ss.playing = START, True
    if ss.playing:
        time.sleep(TICK)
        ss.cursor = min(ss.cursor + 150 * speed, N)
        if ss.cursor < N:
            st.rerun()
        ss.playing = False
        st.toast("shift replay complete")

    alerts = w[w["p_gbt"] >= THR]
    pending = alerts[~alerts["TransactionID"].isin(list(ss.verdicts))]   # oldest first: card stays readable while play runs

    if len(w):
        if len(alerts):
            alarm_line = f"so far, about {cm(w, THR)[4]:.0%} of alarms turned out to be real fraud"
        else:
            alarm_line = "a quiet start - no alarms yet"
        st.markdown(f"**Shift day {day} | {len(w):,} transactions seen | {len(alerts):,} suspicious | "
                    f"{len(ss.verdicts):,} case decisions | {alarm_line}**")

    case_col, feed_col = st.columns([3, 2])
    with case_col:
        st.subheader("Case under review")
        if len(pending):
            r = pending.iloc[0]
            cl, lab = risk(r["p_gbt"])
            st.markdown(f"### Case #{int(r['TransactionID'])} - charge ${r['TransactionAmt']:,.2f} "
                        f"on {card_tag(r['card1'])}")
            st.markdown(f":{cl}[**Suspicion {r['p_gbt']:.0%} - {lab}**]")
            st.progress(float(r["p_gbt"]))
            for x in reasons(r):
                st.markdown("- " + x)
            b1, b2, _ = st.columns([2, 2, 6])
            if b1.button("Confirm fraud", key=f"cf{int(r['TransactionID'])}", use_container_width=True):
                ss.verdicts[int(r["TransactionID"])] = "confirmed"
                st.toast(f"Case #{int(r['TransactionID'])} closed - booked as fraud")
                st.rerun()
            if b2.button("False alarm", key=f"fa{int(r['TransactionID'])}", use_container_width=True):
                ss.verdicts[int(r["TransactionID"])] = "dismissed"
                st.toast(f"Case #{int(r['TransactionID'])} closed - released as clean")
                st.rerun()
        else:
            st.info("Queue clear - close the cases above and more arrive within seconds.")

    with feed_col:
        st.subheader("Notifications")
        for _, rn in w.tail(10).iloc[::-1].iterrows():
            cl = risk(rn["p_gbt"])[0]
            st.markdown(f":{cl}[●] ${rn['TransactionAmt']:,.2f} on {card_tag(rn['card1'])} - "
                        f"suspicion {rn['p_gbt']:.0%} ({size_note(rn['amt_vs_card'])})")

    st.subheader("Cases opened this shift")
    if ss.verdicts:
        lw = w[w["TransactionID"].isin(ss.verdicts)].copy()
        lw["your call"] = lw["TransactionID"].map(ss.verdicts)
        lw["what it really was"] = np.where(lw["isFraud"] == 1, "real fraud", "clean")
        hits = ((lw["your call"] == "confirmed") == (lw["isFraud"] == 1)).sum()
        st.caption(f"{hits:,}/{len(lw):,} of your decisions matched what actually happened")
        st.dataframe(lw[["TransactionID", "your call", "what it really was", "TransactionAmt"]]
                     .rename(columns={"TransactionID": "case", "TransactionAmt": "amount"}), hide_index=True)
    else:
        st.caption("No cases opened yet.")

else:
    st.subheader("Statistics - the science behind the shift")
    t = st.slider("Alarm strictness (how high a suspicion triggers an alarm)", 0.05, 0.95, 0.50, 0.05, format="%.2f")
    band(df, t)
    rows = []
    for x in np.arange(0.05, 0.96, 0.05):
        tp, fp, *_, pr, rc, f1 = cm(df, x)
        rows.append({"threshold": round(x, 2), "alarm accuracy": pr, "fraud found": rc,
                     "balance": f1, "alarms": tp + fp})
    sw = pd.DataFrame(rows)
    b = sw.loc[sw["balance"].idxmax()]
    st.dataframe(sw, hide_index=True)
    st.caption(f"Best all-round alarm level: {b['threshold']} (Phase 4 locked 0.5). "
               "Lower strictness = catch more fraud, more false alarms; higher = fewer, surer alarms.")

    h, fcol = st.columns(2)
    with h:
        st.markdown("**Who gets which score**")
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.hist(df.loc[df["isFraud"] == 0, "p_gbt"], bins=40, alpha=.6, label="clean")
        ax.hist(df.loc[df["isFraud"] == 1, "p_gbt"], bins=40, alpha=.6, color="tomato", label="fraud")
        ax.axvline(t, ls="--", c="k", label=f"alarm level {t:.2f}")
        ax.set_xlabel("model suspicion")
        ax.legend()
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
    with fcol:
        st.markdown("**What the model weighs most**")
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.barh(*zip(*TOP[::-1]), color=["#2a9d8f" if n == "card1_amt_avg" else "#b0b0b0" for n, _ in TOP[::-1]])
        ax.set_title("green = our engineered card-behaviour feature")
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    st.markdown("**Look up one transaction**")
    tid = st.number_input("Transaction ID", step=1, value=int(df["TransactionID"].iloc[0]), label_visibility="collapsed")
    r = df[df["TransactionID"] == int(tid)]
    if r.empty:
        st.warning("no such transaction in the scored window")
    else:
        r = r.iloc[0]
        st.write(f"suspicion **{r['p_gbt']:.0%}** -> **{'alarm' if r['p_gbt'] >= t else 'pass'}** "
                 f"| actually was: **{'fraud' if r['isFraud'] else 'clean'}** | "
                 f"{size_note(r['amt_vs_card'])} | {int(r['card1_txn_24h'])} card charges in 24h")

    st.markdown("**The world this model lives in**")
    e = st.columns(4)
    e[0].metric("overall fraud rate", "3.50%")
    e[1].metric("fraud on tiny charges ($0-1)", "14.47%")
    e[2].metric("cards busy within 24h", "78.4%")
    e[3].metric("busiest card in a day", "881 charges")