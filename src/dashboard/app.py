"""Fraud Watch - the fraud officer's shift screen.
Replays the labeled 17-day future window using the Phase-4 GBT-d5 scores read
offline from CSV; no Spark in the UI. The science lives in the Statistics tab."""
import glob, os
import time
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

LIVE = "data/stream/alerts"                      # notebook-07 parquet sink (spark-written)
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


RC = {"red": "#e5484d", "orange": "#f5a524", "green": "#22a06b"}     # risk word -> hex for the html pieces


def meter(p, cl):                                # the case card's suspicion bar, colored by risk
    st.markdown(f'<div style="height:10px;background:#eceaf6;border-radius:999px;overflow:hidden">'
                f'<div style="height:10px;width:{p:.0%};background:{RC[cl]};border-radius:999px"></div></div>',
                unsafe_allow_html=True)


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
st.markdown("""<style>            /* watch-desk light theme: soft cards, purple accent, Inter */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
.stApp {background:#f6f5fb; color:#1d1d27; font-family:"Inter","Segoe UI",system-ui,sans-serif}
[data-testid="stHeader"] {background:transparent}
section[data-testid="stSidebar"] {background:#fff; border-right:1px solid #e8e6f3; font-family:"Inter","Segoe UI",sans-serif}
section[data-testid="stSidebar"] h1 {font-size:1.35rem; font-weight:800; border-bottom:3px solid #5b4cff; padding-bottom:8px}
h2 {font-size:1.05rem; font-weight:800; border-left:4px solid #5b4cff; padding-left:8px; letter-spacing:-.01em}
h3 {font-weight:800}
[data-testid="stMarkdownContainer"] p {color:#1d1d27}
[data-testid="stMetric"] {background:#fff; border:1px solid #e8e6f3; border-radius:12px; padding:12px;
                          box-shadow:0 1px 2px rgba(29,29,39,.04)}
[data-testid="stMetricLabel"] p {color:#6f6f7c; text-transform:uppercase; letter-spacing:.06em; font-size:.7rem}
[data-testid="stMetricValue"] {font-weight:800}
[data-testid="stMarkdownContainer"] code {background:#f0eefc; color:#5b4cff; border-radius:6px;
                                          padding:1px 5px; font-weight:600}
.stButton>button {background:#fff; color:#1d1d27; border:1px solid #d9d5ee; border-radius:999px; font-weight:600}
.stButton>button:hover {border-color:#5b4cff; color:#5b4cff}
[class*="st-key-cf"] button {background:#22a06b; border-color:#22a06b; color:#fff}
[class*="st-key-fa"] button {background:#e5484d; border-color:#e5484d; color:#fff}
div[data-testid="stProgress"] > div {background:#eceaf6; border-radius:999px}
div[data-testid="stProgress"] div[role="progressbar"] > div {background:#5b4cff}
div[data-testid="stCaptionContainer"] p {color:#6f6f7c; font-size:.85rem}
[data-testid="stDataFrame"] {border:1px solid #e8e6f3; border-radius:12px}
</style>""", unsafe_allow_html=True)
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
    feed = st.radio("Feed", ["Replay", "Live"], key="feed", disabled=mode != "Shift screen")
    speed = st.slider("Replay speed (x)", 1, 10, 3, disabled=(mode != "Shift screen") or feed == "Live")

if mode == "Shift screen":
    if feed == "Live":                           # the live shift starts on THIS page visit - empty
        parts = [f for f in glob.glob(LIVE + "/*.parquet") if os.path.getsize(f) > 0]
        if not parts:
            st.info("No live alerts yet - launch the tier: run_dashboard.ps1 -Live (or notebook 07, cells 1-2).")
            time.sleep(3)
            st.rerun()
        ss.setdefault("fseen", frozenset(parts))           # baseline: sink files present when the page opened
        ss.setdefault("buf", pd.DataFrame(columns=["TransactionID", "TransactionAmt", "day", "isFraud", "p_gbt"]))
        fresh = [f for f in parts if f not in ss.fseen]    # arrival-time truth: a re-run pass legitimately re-alerts
        if fresh:
            ctx = df.drop(columns=["isFraud", "p_gbt", "TransactionAmt", "day", "TransactionDT"]).set_index("TransactionID")
            add = (pd.concat([pd.read_parquet(f) for f in fresh], ignore_index=True)
                   .drop_duplicates("TransactionID").join(ctx, on="TransactionID")
                   .rename(columns={"p_fraud": "p_gbt"}))
            ss.buf = add if not len(ss.buf) else pd.concat([ss.buf, add], ignore_index=True)
            ss.fseen = ss.fseen | frozenset(fresh)
        w = ss.buf                                         # the accumulated live shift
        if not len(w):
            st.caption("LIVE - page open, waiting for the stream to start scoring "
                       "(launch with .\\run_dashboard.ps1 -Live). Polling every 3 s.")
        else:
            day = int(w.iloc[-1]["day"])
            st.caption(f"LIVE - alert queue: {len(w):,} new alerts since this page opened (day {day}); "
                       f"the full population lives in Replay. Auto-refresh every 3 s.")

    else:                                        # the replay engine, unchanged
        w = df.iloc[: ss.cursor]                     # transactions seen so far
        day = int(w.iloc[-1]["day"])
        st.progress(ss.cursor / N, text=f"shift progress - day {day} of 183 (replaying future days 166-182)")
        c1, c2, _ = st.columns([3, 3, 6])
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
    pending = alerts[~alerts["TransactionID"].isin(list(ss.verdicts))]   # undecided cases...
    if feed == "Live":
        pending = pending.sort_values("p_gbt", ascending=False)          # ...worst first - triage like a real desk
    else:
        pending = pending.sort_index()                                   # ...oldest first - readable while replay runs

    if len(w):
        if len(alerts):
            alarm_line = f"so far, about {cm(w, THR)[4]:.0%} of alarms turned out to be real fraud"
        else:
            alarm_line = "a quiet start - no alarms yet"
        if feed == "Live":
            try:
                sent = int(open("data/stream/sent.txt").read())     # producer's pass progress
            except (OSError, ValueError):
                sent = 0
            head = (f"{len(w):,} alerts in the queue (of {sent:,} transactions scored)" if sent
                    else f"{len(w):,} alerts in the queue (pass starting)")
        else:
            head = f"{len(w):,} of {N:,} transactions seen (full population) | {len(alerts):,} suspicious"
        st.markdown(f"**Shift day {day} | {head} | {len(ss.verdicts):,} case decisions | {alarm_line}**")

    case_col, feed_col = st.columns([3, 2])
    with case_col:
        st.subheader("Case under review")
        if len(pending):
            r = pending.iloc[0]
            cl, lab = risk(r["p_gbt"])
            st.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin:2px 0 10px">'
                        f'<div style="min-width:46px;height:46px;border-radius:50%;background:#f0eefc;color:#5b4cff;'
                        f'display:flex;align-items:center;justify-content:center;font-weight:800">'
                        f'{int(r["card1"]) % 1000:03d}</div>'
                        f'<div><div style="font-weight:800;font-size:1.05rem">Case #{int(r["TransactionID"])}</div>'
                        f'<div style="color:#6f6f7c">${r["TransactionAmt"]:,.2f} on card ...{int(r["card1"]) % 1000:03d}'
                        f'</div></div></div>', unsafe_allow_html=True)
            st.markdown(f":{cl}[**Suspicion {r['p_gbt']:.0%} - {lab}**]")
            meter(float(r["p_gbt"]), cl)
            for x in reasons(r):
                st.markdown("- " + x)
            b1, b2, _ = st.columns([2, 2, 6])
            if b1.button("Confirm fraud", key="cf", use_container_width=True):     # stable key: no widget-identity churn between cases
                ss.verdicts[int(r["TransactionID"])] = "confirmed"
                st.toast(f"Case #{int(r['TransactionID'])} closed - booked as fraud")
                st.rerun()
            if b2.button("False alarm", key="fa", use_container_width=True):
                ss.verdicts[int(r["TransactionID"])] = "dismissed"
                st.toast(f"Case #{int(r['TransactionID'])} closed - released as clean")
                st.rerun()
        else:
            st.info("Queue clear - close the cases above and more arrive within seconds.")

    with feed_col:
        st.subheader("Notifications")
        rows = "".join(f'<div style="background:#fff;border:1px solid #e8e6f3;border-radius:10px;padding:8px 10px;'
                       f'margin-bottom:6px;font-size:.85rem"><span style="color:{RC[risk(rn["p_gbt"])[0]]};'
                       f'font-weight:800">&#9679;</span> <b>${rn["TransactionAmt"]:,.2f}</b> on card '
                       f'...{int(rn["card1"]) % 1000:03d} <span style="color:#6f6f7c">- suspicion '
                       f'{rn["p_gbt"]:.0%} ({size_note(rn["amt_vs_card"])})</span></div>'
                       for _, rn in w.tail(10).iloc[::-1].iterrows())
        st.markdown(rows or '<i style="color:#6f6f7c">waiting for the first alert...</i>', unsafe_allow_html=True)

    st.subheader("Cases opened this shift")
    if ss.verdicts:
        order = list(ss.verdicts)[::-1]                      # decisions in reverse - most recent call on top
        lw = (w[w["TransactionID"].isin(order)]
              .set_index("TransactionID"))
        lw = lw.loc[[i for i in order if i in lw.index]].reset_index()   # a decision may predate this window
        if len(lw):
            call = lw["TransactionID"].map(ss.verdicts)
            hits = (call == "confirmed").eq(lw["isFraud"] == 1).sum()
            lw["your call"] = call.map({"confirmed": "Confirm fraud", "dismissed": "False alarm"})
            lw["what it really was"] = np.where(lw["isFraud"] == 1, "fraud", "clean")
            st.caption(f"{hits:,}/{len(lw):,} of your decisions matched what actually happened")
            st.dataframe(lw[["TransactionID", "your call", "what it really was", "TransactionAmt"]]
                         .rename(columns={"TransactionID": "case", "TransactionAmt": "amount"}), hide_index=True)
        else:
            st.caption("Decisions exist, but none in this feed's window yet - switch feed or let replay reach them.")
    else:
        st.caption("No cases opened yet.")

    if feed == "Live":                           # saving throw: re-read the sink every 3 s
        time.sleep(3)
        st.rerun()

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