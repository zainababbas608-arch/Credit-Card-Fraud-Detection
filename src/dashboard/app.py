"""Fraud Watch - the fraud officer's shift screen.
Replays the labeled 17-day future window using the Phase-4 GBT-d5 scores read
offline from CSV; no Spark in the UI. The science lives in the Statistics tab."""
import glob, os, time
import numpy as np, pandas as pd, streamlit as st
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

LIVE, CSV, THR, TICK = "data/stream/alerts", "data/processed/dashboard_test.csv", 0.5, 0.25
TOP = [("V258",5.5),("C13",4.6),("C1",4.4),("TransactionAmt",4.1),("card1_amt_avg",4.0),
       ("C14",3.9),("C11",3.5),("day",3.0),("card6_idx",2.6),("card3",2.6)]

def cm(d,t):
    p,y = d["p_gbt"]>=t, d["isFraud"]==1
    tp,fp,fn,tn = int((p&y).sum()),int((p&~y).sum()),int((~p&y).sum()),int((~p&~y).sum())
    pr = tp/(tp+fp) if tp+fp else 0.0; rc = tp/(tp+fn) if tp+fn else 0.0
    return tp,fp,fn,tn,pr,rc,2*pr*rc/(pr+rc) if pr+rc else 0.0

def risk(p): return ("red","HIGH") if p>=0.7 else (("orange","MEDIUM") if p>=0.4 else ("green","low"))
def size_note(a): return "tiny for this card" if a<0.5 else (f"{a:.1f}x the card's usual spend" if a>3 else "usual size for this card")
RC = {"red":"#e5484d","orange":"#f5a524","green":"#22a06b"}

def meter(p,cl):
    st.markdown(f'<div style="height:10px;background:#eceaf6;border-radius:999px;overflow:hidden"><div style="height:10px;width:{p:.0%};background:{RC[cl]};border-radius:999px"></div></div>', unsafe_allow_html=True)

def band(d,t):
    tp,fp,fn,_,pr,rc,f1 = cm(d,t)
    money = d.loc[(d["isFraud"]==1)&(d["p_gbt"]>=t),"TransactionAmt"].sum()
    m = f"${money/1e6:.0f}M" if money>=1e6 else (f"${money/1e3:.0f}K" if money>=1e3 else f"${money:.0f}")
    c = st.columns(6)
    c[0].metric("alarms raised", f"{tp+fp:,}")
    c[1].metric("real fraud caught", f"{tp:,}", f"{fn:,} missed")
    c[2].metric("money at risk", m)
    c[3].metric("alarm accuracy", f"{pr:.3f}", f"{fp:,} false alarms")
    c[4].metric("fraud found", f"{rc:.0%}")
    c[5].metric("balance score (F1)", f"{f1:.3f}")

@st.cache_data
def reband():
    a = df[df["p_gbt"]>=THR]; b = (a["p_gbt"]*10).astype(int).clip(upper=9)
    g = a.groupby(b)["isFraud"].agg(["mean","size"]); return g["mean"], g["size"]

@st.cache_data
def vlevel():
    g = df.groupby("V258")["isFraud"].agg(["size","mean"]); return g["size"]/len(df), g["mean"]/df["isFraud"].mean()

def pill(rn, tail=""):
    cl = risk(rn["p_gbt"])[0]
    return (f'<div style="background:#fff;border:1px solid #e8e6f3;border-radius:10px;padding:8px 10px;margin-bottom:6px;font-size:.85rem"><span style="color:{RC[cl]};font-weight:800">&#9679;</span> <b>${rn["TransactionAmt"]:,.2f}</b> on card ...{int(rn["card1"])%1000:03d} <span style="color:#6f6f7c">suspicion {rn["p_gbt"]:.0%} ({size_note(rn["amt_vs_card"])}{tail}</span></div>')

def evcard(label,big,note):
    st.markdown(f'<div style="background:#fff;border:1px solid #e8e6f3;border-radius:12px;padding:12px 14px"><div style="color:#6f6f7c;font-size:.65rem;letter-spacing:.08em;text-transform:uppercase">{label}</div><div style="font-weight:800;margin:3px 0">{big}</div><div style="font-size:.85rem;color:#6f6f7c">{note}</div></div>', unsafe_allow_html=True)

def addnote(cid):
    x = st.session_state.get("notebox","").strip()
    if x:
        st.session_state.setdefault("notes",{}).setdefault(cid,[]).append((time.strftime("%H:%M"),x))
        st.session_state.notebox = ""

st.set_page_config(page_title="Fraud Watch", layout="wide")
st.markdown("""<style>@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');.stApp{background:#f6f5fb;color:#1d1d27;font-family:"Inter","Segoe UI",system-ui,sans-serif}[data-testid="stHeader"]{background:transparent}section[data-testid="stSidebar"]{background:#fff;border-right:1px solid #e8e6f3;font-family:"Inter","Segoe UI",sans-serif}h1{font-size:1.5rem;font-weight:800;border-bottom:3px solid #5b4cff;padding-bottom:8px;letter-spacing:-.01em}h2{font-size:1.05rem;font-weight:800;border-left:4px solid #5b4cff;padding-left:8px;letter-spacing:-.01em}h3{font-weight:800}[data-testid="stMarkdownContainer"] p{color:#1d1d27}[data-testid="stMetric"]{background:#fff;border:1px solid #e8e6f3;border-radius:12px;padding:12px;box-shadow:0 1px 2px rgba(29,29,39,.04)}[data-testid="stMetricLabel"] p{color:#6f6f7c;text-transform:uppercase;letter-spacing:.06em;font-size:.7rem}[data-testid="stMetricValue"]{font-weight:800}[data-testid="stMarkdownContainer"] code{background:#f0eefc;color:#5b4cff;border-radius:6px;padding:1px 5px;font-weight:600}.stButton>button{background:#fff;color:#1d1d27;border:1px solid #d9d5ee;border-radius:999px;font-weight:600}.stButton>button:hover{border-color:#5b4cff;color:#5b4cff}[class*="st-key-cf"] button{background:#22a06b;border-color:#22a06b;color:#fff}[class*="st-key-fa"] button{background:#e5484d;border-color:#e5484d;color:#fff}div[data-testid="stProgress"] > div{background:#eceaf6;border-radius:999px}div[data-testid="stProgress"] div[role="progressbar"] > div{background:#5b4cff}div[data-testid="stCaptionContainer"] p{color:#6f6f7c;font-size:.85rem}[data-testid="stDataFrame"]{border:1px solid #e8e6f3;border-radius:12px}</style>""", unsafe_allow_html=True)
try:
    @st.cache_data
    def load():
        d = pd.read_csv(CSV); d["isFraud"] = d["isFraud"].astype(int); return d
    df = load()
except FileNotFoundError:
    st.error(f"{CSV} missing - run Cell 17 of 06_full_scale_training.ipynb first."); st.stop()

N, F = len(df), int(df["isFraud"].sum())
START = int(df.index[df["p_gbt"]>=THR][0])
ss = st.session_state
ss.setdefault("cursor",START); ss.setdefault("playing",True); ss.setdefault("verdicts",{}); ss.setdefault("notes",{})

st.title("Fraud Watch")
st.caption(f"Replay of the labeled future window (days 166-182), verdicts from the Phase-4 model read offline. {N:,} transactions | {F:,} real fraud. No Spark in the UI.")
hc1,hc2,hc3 = st.columns([1,1,1.4])
with hc1: mode = st.radio("View",["Shift screen","Statistics"],key="mode",horizontal=True)
with hc2: feed = st.radio("Feed",["Replay","Live"],key="feed",disabled=mode!="Shift screen",horizontal=True)
with hc3: speed = st.slider("Replay speed (x)",1,10,3,disabled=(mode!="Shift screen") or feed=="Live")

if mode == "Shift screen":
    if feed == "Live":
        parts = [f for f in glob.glob(LIVE+"/*.parquet") if os.path.getsize(f)>0]
        if not parts:
            st.info("No live alerts yet - launch the tier: run_dashboard.ps1 -Live (or notebook 07, cells 1-2).")
            time.sleep(3); st.rerun()
        ss.setdefault("fseen",frozenset(parts)); ss.setdefault("seen",frozenset())
        ss.setdefault("buf",pd.DataFrame(columns=["TransactionID","TransactionAmt","day","isFraud","p_gbt"]))
        fresh = [f for f in parts if f not in ss.fseen]
        if fresh:
            ctx = df.drop(columns=["isFraud","p_gbt","TransactionAmt","day","TransactionDT"]).set_index("TransactionID")
            add = (pd.concat([pd.read_parquet(f) for f in fresh],ignore_index=True).drop_duplicates("TransactionID").join(ctx,on="TransactionID").rename(columns={"p_fraud":"p_gbt"}))
            add = add[~add["TransactionID"].isin(list(ss.seen))]
            ss.buf = add if not len(ss.buf) else pd.concat([ss.buf,add],ignore_index=True)
            ss.fseen = ss.fseen | frozenset(fresh)
            ss.seen = ss.seen | frozenset(add["TransactionID"].astype(int))
        w = ss.buf
        if not len(w):
            st.caption("LIVE - page open, waiting for the stream to start scoring (launch with .\\run_dashboard.ps1 -Live). Polling every 3 s.")
        else:
            day = int(w.iloc[-1]["day"])
            st.caption(f"LIVE - alert queue: {len(w):,} new alerts since this page opened (day {day}); the full population lives in Replay. Auto-refresh every 3 s.")
    else:
        w = df.iloc[:ss.cursor]; day = int(w.iloc[-1]["day"])
        st.progress(ss.cursor/N, text=f"shift progress - day {day} of 183 (replaying future days 166-182)")
        c1,c2,_ = st.columns([3,3,6])
        if c1.button("Play/Pause"): ss.playing = not ss.playing
        if c2.button("Reset shift"): ss.cursor, ss.playing = START, True

    alerts = w[w["p_gbt"]>=THR]
    pending = alerts[~alerts["TransactionID"].isin(list(ss.verdicts))].sort_index()
    if len(w):
        alarm_line = f"so far, about {cm(w,T)[4]:.0%} of alarms turned out to be real fraud" if len(alerts) else "a quiet start - no alarms yet"
        if feed == "Live":
            try: sent = int(open("data/stream/sent.txt").read())
            except (OSError,ValueError): sent = 0
            head = f"{len(w):,} alerts in the queue (of {sent:,} transactions scored)" if sent else f"{len(w):,} alerts in the queue (pass starting)"
        else:
            head = f"{len(w):,} of {N:,} transactions seen (full population) | {len(alerts):,} suspicious"
        st.markdown(f"**Shift day {day} | {head} | {len(ss.verdicts):,} case decisions | {alarm_line}**")

    case_col = st.container()
    with case_col:
        st.subheader("Case under review")
        if len(pending):
            r = pending.iloc[0]; cl,lab = risk(r["p_gbt"])
            st.markdown(f'<div style="display:flex;align-items:center;gap:12px;margin:2px 0 10px"><div style="min-width:46px;height:46px;border-radius:50%;background:#f0eefc;color:#5b4cff;display:flex;align-items:center;justify-content:center;font-weight:800">{int(r["card1"])%1000:03d}</div><div><div style="font-weight:800;font-size:1.05rem">Case #{int(r["TransactionID"])}</div><div style="color:#6f6f7c">${r["TransactionAmt"]:,.2f} on card ...{int(r["card1"])%1000:03d}</div></div></div>', unsafe_allow_html=True)
            st.markdown(f'<span style="display:inline-block;padding:4px 14px;border-radius:999px;background:{RC[cl]}1f;color:{RC[cl]};font-weight:800">Suspicion {r["p_gbt"]:.0%} - {lab}</span>', unsafe_allow_html=True)
            meter(float(r["p_gbt"]),cl)
            pr,pn = reband(); b = min(int(r["p_gbt"]*10),9)
            st.caption(f"reliability: among alarms scored {b/10:.0%}-{(b+1)/10:.0%}, {pr[b]:.0%} were real fraud ({pn[b]:,} measured)")
            n24 = int(r["card1_txn_24h"]); a = r["amt_vs_card"]
            a_note = ("small-charge burst - the card-testing signature" if r["TransactionAmt"]<10 and n24>3 else size_note(a))
            sh,en = vlevel(); sh,en = sh.loc[r["V258"]], en.loc[r["V258"]]
            if sh>=0.2: v_big,v_note = "ordinary pattern", (f"the hidden-risk level (V258) that {sh:.0%} of transactions share - fraud is rarer here than average")
            elif en>=0.99: v_big,v_note = "rarest tier","this hidden-risk level (V258) appears in a handful of transactions - every one was fraud"
            else: v_big,v_note = "rare pattern", (f"only {sh:.2%} of transactions reach this hidden-risk level (V258) - fraud runs {en:.0f}x more common here")
            e1,e2,e3 = st.columns([1.2,0.8,1.2])
            with e1: evcard("amount",f"${r['TransactionAmt']:,.2f}",a_note)
            with e2: evcard("card",f"...{int(r['card1'])%1000:03d}",f"{n24} charges in 24h")
            with e3: evcard("risk pattern",v_big,v_note)
            b1,bgap,b2,_ = st.columns([1,0.12,1,1.1])
            if b1.button("Confirm fraud",key="cf",use_container_width=True):
                ss.verdicts[int(r["TransactionID"])] = "confirmed"; st.toast(f"Case #{int(r['TransactionID'])} closed - booked as fraud"); st.rerun()
            if b2.button("False alarm",key="fa",use_container_width=True):
                ss.verdicts[int(r["TransactionID"])] = "dismissed"; st.toast(f"Case #{int(r['TransactionID'])} closed - released as clean"); st.rerun()
            cid = int(r["TransactionID"]); notes = ss.notes.get(cid,[])
            st.caption(f"Case notes ({len(notes)})")
            for ts,x in reversed(notes):
                st.markdown(f'<div style="background:#fff;border:1px solid #e8e6f3;border-radius:10px;padding:6px 10px;margin-bottom:4px;font-size:.85rem"><b style="color:#5b4cff">{ts}</b> - {x}</div>', unsafe_allow_html=True)
            ti,nb = st.columns([2,1])
            ti.text_input("Add a note",key="notebox",label_visibility="collapsed")
            nb.button("Add note",key="an",on_click=addnote,kwargs={"cid":cid})
        else:
            st.info("Queue clear - close the cases above and more arrive within seconds.")
    with st.sidebar:
        st.subheader("Notifications")
        st.caption("queue - the top pill is the case under review; decided cases drop into the log")
        worst = pending.sort_values("p_gbt").iloc[-1] if len(pending) else None
        triage = (f'<div style="color:#6f6f7c;font-size:.8rem;margin-bottom:6px">worst still waiting: {worst["p_gbt"]:.0%} (case #{int(worst["TransactionID"])})</div>' if worst is not None else "")
        q = "".join(pill(rn) for _,rn in pending.head(15).iterrows())
        more = (f'<div style="color:#6f6f7c;font-size:.8rem">+ {len(pending)-15:,} more waiting</div>' if len(pending)>15 else "")
        st.markdown(triage+q+more or '<i style="color:#6f6f7c">queue clear - no alerts waiting</i>', unsafe_allow_html=True)
        if ss.verdicts:
            done = [(cid,ss.verdicts[cid]) for cid in list(ss.verdicts)[::-1]][:8]
            dz = alerts[alerts["TransactionID"].isin([c for c,_ in done])].set_index("TransactionID")
            log = "".join(pill(dz.loc[c], f' - <b style="color:{RC["green" if v=="confirmed" else "red"]}">{"booked as fraud" if v=="confirmed" else "released as clean"}</b>') for c,v in done if c in dz.index)
            if log:
                st.caption("handled"); st.markdown(log, unsafe_allow_html=True)
    st.subheader("Cases opened this shift")
    if ss.verdicts:
        order = list(ss.verdicts)[::-1]
        lw = w[w["TransactionID"].isin(order)].set_index("TransactionID")
        lw = lw.loc[[i for i in order if i in lw.index]].reset_index()
        if len(lw):
            call = lw["TransactionID"].map(ss.verdicts)
            hits = (call=="confirmed").eq(lw["isFraud"]==1).sum()
            lw["your call"] = call.map({"confirmed":"Confirm fraud","dismissed":"False alarm"})
            lw["what it really was"] = np.where(lw["isFraud"]==1,"fraud","clean")
            st.caption(f"{hits:,}/{len(lw):,} of your decisions matched what actually happened")
            lw["amount"] = lw["TransactionAmt"].map(lambda a: f"${a:,.2f}")
            st.dataframe(lw[["TransactionID","your call","what it really was","amount"]].rename(columns={"TransactionID":"case"}), hide_index=True)
        else:
            st.caption("Decisions exist, but none in this feed's window yet - switch feed or let replay reach them.")
    else:
        st.caption("No cases opened yet.")
    if feed=="Replay" and ss.playing:
        time.sleep(TICK); ss.cursor = min(ss.cursor+150*speed,N)
        if ss.cursor<N: st.rerun()
        ss.playing = False; st.toast("shift replay complete")
    if feed=="Live":
        time.sleep(3); st.rerun()
else:
    st.subheader("Statistics - the science behind the shift")
    t = st.slider("Alarm strictness (how high a suspicion triggers an alarm)",0.05,0.95,0.50,0.05,format="%.2f")
    band(df,t)
    rows = []
    for x in np.arange(0.05,0.96,0.05):
        tp,fp,*_,pr,rc,f1 = cm(df,x)
        rows.append({"threshold":round(x,2),"alarm accuracy":pr,"fraud found":rc,"balance":f1,"alarms":tp+fp})
    sw = pd.DataFrame(rows); b = sw.loc[sw["balance"].idxmax()]
    st.dataframe(sw, hide_index=True)
    st.caption(f"Best all-round alarm level: {b['threshold']} (Phase 4 locked 0.5). Lower strictness = catch more fraud, more false alarms; higher = fewer, surer alarms.")
    h,fcol = st.columns(2)
    with h:
        st.markdown("**Who gets which score**")
        fig,ax = plt.subplots(figsize=(6,4))
        ax.hist(df.loc[df["isFraud"]==0,"p_gbt"],bins=40,alpha=.6,label="clean")
        ax.hist(df.loc[df["isFraud"]==1,"p_gbt"],bins=40,alpha=.6,color="tomato",label="fraud")
        ax.axvline(t,ls="--",c="k",label=f"alarm level {t:.2f}")
        ax.set_xlabel("model suspicion"); ax.legend()
        st.pyplot(fig, use_container_width=True); plt.close(fig)
    with fcol:
        st.markdown("**What the model weighs most**")
        fig,ax = plt.subplots(figsize=(6,4))
        ax.barh(*zip(*TOP[::-1]), color=["#2a9d8f" if n=="card1_amt_avg" else "#b0b0b0" for n,_ in TOP[::-1]])
        ax.set_title("green = our engineered card-behaviour feature")
        st.pyplot(fig, use_container_width=True); plt.close(fig)
    st.markdown("**Look up one transaction**")
    tid = st.number_input("Transaction ID",step=1,value=int(df["TransactionID"].iloc[0]),label_visibility="collapsed")
    r = df[df["TransactionID"]==int(tid)]
    if r.empty: st.warning("no such transaction in the scored window")
    else:
        r = r.iloc[0]
        st.write(f"suspicion **{r['p_gbt']:.0%}** -> **{'alarm' if r['p_gbt']>=t else 'pass'}** | actually was: **{'fraud' if r['isFraud'] else 'clean'}** | {size_note(r['amt_vs_card'])} | {int(r['card1_txn_24h'])} card charges in 24h")
    st.markdown("**The world this model lives in**")
    e = st.columns(4)
    e[0].metric("overall fraud rate","3.50%")
    e[1].metric("fraud on tiny charges ($0-1)","14.47%")
    e[2].metric("cards busy within 24h","78.4%")
    e[3].metric("busiest card in a day","881 charges")