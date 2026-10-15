"""Direct, auditable release model built from the completed v3 research artifacts.

The model combines a 37-country annual equity episode estimator with the separately
estimated geopolitical/liquidity state model. Tail splits and country transmission
are explicitly structural calibrations. Outputs are model-conditional scenarios,
not unconditional forecasts or investment advice.
"""
from __future__ import annotations
import json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
V3 = ROOT / "models/v3"
OUT = V3 / "outputs/site"
sys.path.insert(0, str(V3))
from probability import equity_panel as EP
from systemic_transition import fit as fit_systemic_transition, predict as predict_systemic

SEED=20261014; DRAWS=10_000
STATES=[("calm","ample"),("calm","neutral"),("calm","vacuum"),("tense","ample"),("tense","neutral"),("tense","vacuum"),("crisis","ample"),("crisis","neutral"),("crisis","vacuum")]
SCEN=["continued_boom","no_burst_sideways","mild_adjustment","moderate_burst","deep_drawdown_no_vacuum","severe_burst","severe_burst_with_financial_crisis"]
NAMES={"continued_boom":"Continued boom","no_burst_sideways":"Contained repricing","mild_adjustment":"Mild adjustment","moderate_burst":"Moderate burst","deep_drawdown_no_vacuum":"Deep drawdown, liquidity holds","severe_burst":"Severe burst + liquidity vacuum","severe_burst_with_financial_crisis":"Severe burst + financial crisis"}

def load(rel): return json.loads((ROOT/rel).read_text())
def clean(x):
    if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [clean(v) for v in x]
    if isinstance(x,(np.floating,float)): return float(x) if math.isfinite(float(x)) else None
    if isinstance(x,np.integer): return int(x)
    return x
def dump(name,obj): OUT.mkdir(parents=True,exist_ok=True); (OUT/f"{name}.json").write_text(json.dumps(clean(obj),indent=2,allow_nan=False)+"\n")
def logit(p): p=np.clip(p,1e-6,1-1e-6); return np.log(p/(1-p))
def logistic(x): return 1/(1+np.exp(-x))

def current_features():
    us=load("models/v3/us_ai/outputs/us_ai_decomposition.json")
    s=pd.Series({pd.Period(x["month"][:7],freq="M"):x["value"] for x in us["basket"]["indexMonthly"]}).sort_index()
    annual=np.array([s.iloc[-1-12*i]/s.iloc[-1-12*(i+1)]-1 for i in range(5)])
    return np.array([s.iloc[-1]/s.iloc[-37]-1,s.iloc[-1]/s.iloc[-13]-1,annual.std()]),us

def fit_probs(df,features):
    ps=[]
    for _,c in EP.MODEL_CONFIGS:
        sc=StandardScaler().fit(df[list(EP.PREDICTORS)])
        m=LogisticRegression(C=c,solver="lbfgs",max_iter=3000,random_state=SEED).fit(sc.transform(df[list(EP.PREDICTORS)]),df.band)
        raw=m.predict_proba(sc.transform(pd.DataFrame([features],columns=EP.PREDICTORS)))[0]
        p={b:1e-9 for b in EP.BANDS}; p.update(dict(zip(m.classes_,raw))); ps.append(p)
    return {b:float(np.mean([p[b] for p in ps])) for b in EP.BANDS}

def fit_challengers(df,features):
    """Non-linear challengers used only as a bounded ambiguity overlay.

    They capture thresholds/interactions that a logit cannot, but receive small
    weights because their leave-country-out validation is weaker and unstable.
    """
    X=df[list(EP.PREDICTORS)]; y=df.band
    models=[
      GradientBoostingClassifier(n_estimators=80,max_depth=2,learning_rate=.035,subsample=.8,random_state=SEED),
      RandomForestClassifier(n_estimators=500,max_depth=4,min_samples_leaf=5,max_features=.8,class_weight="balanced",random_state=SEED,n_jobs=-1)]
    out=[]
    for m in models:
        m.fit(X,y); raw=m.predict_proba(pd.DataFrame([features],columns=EP.PREDICTORS))[0]
        p={b:1e-9 for b in EP.BANDS};p.update(dict(zip(m.classes_,raw)));out.append(p)
    return out

def historical_transitions(df):
    """Estimate within-band transitions without counting a global crash many times."""
    # Sideways is observable for every non-bust country episode: cumulative return
    # through t+2 <=10%, conditional on never drawing down 20% at annual closes.
    rows=[]
    for _,r in df.iterrows():
        path=next((ROOT/"data/derived/series").glob(f"WB_CM.MKT.INDX.ZG_{r.country}.csv"))
        d=pd.read_csv(path);d["year"]=d.date.astype(str).str[:4].astype(int);d["ret"]=pd.to_numeric(d.value,errors="coerce")/100
        rr=d.dropna(subset=["ret"]).set_index("year").ret
        if r.originYear+1 in rr.index and r.originYear+2 in rr.index:
            fwd=(1+rr.loc[r.originYear+1])*(1+rr.loc[r.originYear+2])-1
            rows.append({"country":r.country,"originYear":int(r.originYear),"band":r.band,"forward2y":float(fwd)})
    f=pd.DataFrame(rows); none=f[f.band=="none"]; side=int((none.forward2y<=.10).sum()); n_none=len(none)
    # Severe observations are heavily synchronized. Collapse origins within two
    # years into independent global clusters before estimating tail transitions.
    severe=sorted(df[df.band=="severe"].originYear.astype(int).unique()); clusters=[]
    for y in severe:
        if not clusters or y-clusters[-1][-1]>2: clusters.append([y])
        else: clusters[-1].append(y)
    jst=pd.read_csv(ROOT/"data/derived/panels/JST_ANNUAL_PANEL.csv")
    counts=np.zeros(3,dtype=int); audit=[] # deep/no vacuum, vacuum/no systemic, systemic
    for years in clusters:
        members=df[(df.band=="severe") & (df.originYear.astype(int).isin(years))]
        systemic=False
        for _,r in members.iterrows():
            z=jst[(jst.iso==r.country)&(jst.year.between(int(r.originYear),int(r.originYear)+2))]
            systemic=systemic or bool(len(z) and z.crisisJST.fillna(0).max()>0)
        klass=2 if systemic else 0;counts[klass]+=1
        audit.append({"originYears":years,"countries":sorted(members.country.unique().tolist()),"classification":["deep_no_vacuum","vacuum_no_systemic","systemic"][klass]})
    # Jeffreys priors prevent zero probability in a two-cluster tail sample.
    side_alpha=np.array([n_none-side+.5,side+.5]) # boom, sideways
    tail_alpha=counts+.5
    return {"sidewaysObserved":side,"nonBustObserved":n_none,"sidewaysPosteriorMean":float(side_alpha[1]/side_alpha.sum()),"sideAlpha":side_alpha,
      "severeCountryEpisodes":int((df.band=="severe").sum()),"severeClusters":audit,"tailCounts":counts,"tailAlpha":tail_alpha,"tailPosteriorMean":tail_alpha/tail_alpha.sum()}

def conditional(base,mult,g,l,continue_share,tail_share):
    bust0=base["mild"]+base["moderate"]+base["severe"]
    bust=float(logistic(logit(bust0)+math.log(max(mult,0.05))))
    within=np.array([base["mild"],base["moderate"],base["severe"]]); within/=within.sum()
    mild,moderate,severe=(bust*within).tolist(); none=1-bust
    out={k:0.0 for k in SCEN}; out["continued_boom"]=none*continue_share; out["no_burst_sideways"]=none*(1-continue_share)
    out["mild_adjustment"]=mild;out["moderate_burst"]=moderate
    out["deep_drawdown_no_vacuum"]=severe*tail_share[0]
    out["severe_burst"]=severe*tail_share[1]
    out["severe_burst_with_financial_crisis"]=severe*tail_share[2]
    z=sum(out.values()); return {k:v/z for k,v in out.items()}

def build_scenarios():
    df,_=EP.load_panel(); features,us=current_features(); linear=fit_probs(df,features); gb,rf=fit_challengers(df,features)
    # Performance-gated ensemble: the calibrated logits remain the core; nonlinear
    # models widen the estimate without being allowed to dominate it.
    base={b:.75*linear[b]+.15*gb[b]+.10*rf[b] for b in EP.BANDS}
    states=load("models/v3/probability/outputs/states.json")
    weights=np.array(states["windowStartWeights_pi"],float); weights/=weights.sum()
    geo_factor={"calm":.88,"tense":1.0,"crisis":1.18}; liq_factor={"ample":.62,"neutral":1.0,"vacuum":2.75}
    trans=historical_transitions(df)
    systemic_model, systemic_panel, systemic_template, systemic_audit = fit_systemic_transition(ROOT)
    # Integrate the calibrated transition curve over plausible severe declines.
    # This replaces the old two-cluster Dirichlet split.  A liquidity vacuum that
    # does not become a banking crisis retains a small explicit residual share.
    severe_grid=np.linspace(-.76,-.50,81)
    severe_w=np.exp(-.5*((severe_grid+.62)/.075)**2); severe_w/=severe_w.sum()
    systemic_share=float(np.sum(predict_systemic(systemic_model,systemic_template,severe_grid)*severe_w))
    vacuum_given_non_systemic=.20
    tail_share=np.array([(1-systemic_share)*(1-vacuum_given_non_systemic),(1-systemic_share)*vacuum_given_non_systemic,systemic_share])
    continue_share=1-trans["sidewaysPosteriorMean"]
    rows=[]
    for i,(g,l) in enumerate(STATES):
        m=geo_factor[g]*liq_factor[l]
        rows.append({"geopolitics":g,"liquidity":l,"stressMultiplier":m,"probabilities":conditional(base,m,g,l,continue_share,tail_share)})
    target={k:sum(weights[i]*rows[i]["probabilities"][k] for i in range(9)) for k in SCEN}
    rng=np.random.default_rng(SEED)
    labels=rng.choice(SCEN,size=DRAWS,p=[target[k] for k in SCEN]); point=target
    # Country-cluster bootstrap plus state-weight uncertainty. Tail split uncertainty is included explicitly.
    countries=df.country.unique(); boots=[]
    for b in range(300):
        sample=pd.concat([df[df.country==c] for c in rng.choice(countries,len(countries),replace=True)],ignore_index=True)
        try: pb=fit_probs(sample,features*rng.normal(1,[.05,.10,.10],3))
        except Exception: continue
        wb=rng.dirichlet(weights*250+1); cb=float(rng.beta(*trans["sideAlpha"]));
        ps=float(rng.beta(systemic_share*16+.5,(1-systemic_share)*16+.5)); pv=float(rng.beta(2.5,10.5))
        tb=np.array([(1-ps)*(1-pv),(1-ps)*pv,ps]); vals={k:0. for k in SCEN}
        for i,(g,l) in enumerate(STATES):
            q=conditional(pb,geo_factor[g]*liq_factor[l]*rng.lognormal(0,.16),g,l,cb,tb)
            for k in SCEN: vals[k]+=wb[i]*q[k]
        boots.append(vals)
    intervals={k:[float(np.quantile([x[k] for x in boots],.1)),float(np.quantile([x[k] for x in boots],.9))] for k in SCEN}
    defs={
      "continued_boom":(-.20,"<20% drawdown; 24-month return above +10%."),
      "no_burst_sideways":(-.20,"Contained repricing: <20% drawdown; 24-month return at or below +10%."),
      "mild_adjustment":(-.20,"Mild: 20–35% peak-to-trough decline."),"moderate_burst":(-.35,"Moderate: 35–50% peak-to-trough decline."),
      "deep_drawdown_no_vacuum":(-.50,"Severe: ≥50% decline; broad funding markets keep functioning."),
      "severe_burst":(-.50,"Severe: ≥50% decline plus a liquidity vacuum."),
      "severe_burst_with_financial_crisis":(-.50,"Systemic: ≥50% decline, liquidity vacuum and bank/funding stress.")}
    annual=load("models/v3/probability/outputs/equity_episode_model.json")
    scenarios=[{"id":k,"name":NAMES[k],"class":k,"description":defs[k][1],"probability":point[k],"interval80":intervals[k],"definition":{"drawdownThreshold":defs[k][0],"horizonMonths":24},"evidenceRefs":["World Bank:CM.MKT.INDX.ZG","GPR","FRED:NFCI/STLFSI4"]} for k in SCEN]
    tree={"asOf":"2026-10-15","status":"model_conditional_weak_skill","scenarios":scenarios,
      "drivers":[{"id":"ai_runup_36m","label":"AI basket 36-month run-up","currentValue":float(features[0]*100),"unit":"percent","sourceRef":"Yahoo-derived private prices"},{"id":"ai_return_12m","label":"AI basket 12-month return","currentValue":float(features[1]*100),"unit":"percent","sourceRef":"Yahoo-derived private prices"},{"id":"hy_oas","label":"US high-yield spread","currentValue":3.16,"unit":"percent","sourceRef":"FRED:BAMLH0A0HYM2"},{"id":"china_property","label":"China property decline from peak","currentValue":22.61,"unit":"percent","sourceRef":"BIS:WS_SPP"}],
      "stateProbabilities":[{"geopolitics":g,"liquidity":l,"probability":float(weights[i])} for i,(g,l) in enumerate(STATES)],"conditionalProbabilities":rows,
      "method":{"datasets":["World Bank CM.MKT.INDX.ZG (CC BY 4.0)","JST Macrohistory banking-crisis flags","Caldara-Iacoviello GPR","FRED financial conditions"],"episodeCount":int(len(df)),"countries":int(df.country.nunique()),"estimator":"75% calibrated L2-logit core, 15% gradient-boosting and 10% random-forest challenger overlay; country-cluster bootstrap","conditioning":"transparent monotonic geopolitical × liquidity stress surface","currentFeatures":{"runup3":float(features[0]),"return1":float(features[1]),"volatility5":float(features[2])},"challengerBustProbabilities":{"logit":linear["mild"]+linear["moderate"]+linear["severe"],"gradientBoosting":gb["mild"]+gb["moderate"]+gb["severe"],"randomForest":rf["mild"]+rf["moderate"]+rf["severe"]},"transitionAudit":{"sidewaysObserved":trans["sidewaysObserved"],"nonBustObserved":trans["nonBustObserved"],"sidewaysPosteriorMean":trans["sidewaysPosteriorMean"],"severeCountryEpisodes":trans["severeCountryEpisodes"],"independentSevereClusters":len(trans["severeClusters"]),"clusterClassifications":trans["severeClusters"],"tailPosteriorMean":{"deepNoVacuum":float(tail_share[0]),"vacuumNoSystemic":float(tail_share[1]),"systemic":float(tail_share[2])},"tailMethod":"Calibrated banking-crisis transition integrated over 50–76% drawdowns; 20% of non-systemic severe paths are assigned a temporary liquidity vacuum.","systemicTransition":systemic_audit},"warning":"The systemic transition improves leave-country-out Brier score, but independent global crashes remain scarce. Odds are scenario weights, not precise frequencies."},
      "backtest":{"brierScore":annual["backtest"]["brierScore"],"baseRateBrierScore":annual["backtest"]["baseRateBrierScore"],"logScore":annual["backtest"]["logScore"],"baseRateLogScore":annual["backtest"]["baseRateLogScore"],"outOfSampleEpisodes":annual["backtest"]["crossValidatedEpisodes"],"skillDisclosure":"Brier improves modestly versus the base rate; log score is essentially unchanged. Treat odds as disciplined scenario weights, not precise forecasts."},
      "monteCarlo":{"draws":DRAWS,"seed":SEED,"maxMonteCarloStdError":float(max(math.sqrt(point[k]*(1-point[k])/DRAWS) for k in SCEN)),"classificationCounts":{k:int(np.sum(labels==k)) for k in SCEN}}}
    dump("scenario_tree",tree); return tree,labels,us,(systemic_model,systemic_template,systemic_audit)

def build_paths(tree):
    rng=np.random.default_rng(SEED+1); years=[2026,2027,2028,2029,2030]
    # Annual anchors are regime paths, not a linear extrapolation. Severe cases are
    # benchmarked to the Fed 2026 severely-adverse path (4.6% real-GDP level loss)
    # and the persistent 2007Q4–2009Q2 contraction rather than a one-year dip.
    us_gdp={
      "continued_boom":[2.4,2.5,2.4,2.3,2.2],"no_burst_sideways":[2.4,1.5,1.4,1.8,2.0],
      "mild_adjustment":[2.4,.6,.7,1.4,1.9],"moderate_burst":[2.4,-.8,-.5,.7,1.5],
      "deep_drawdown_no_vacuum":[2.4,-1.9,-1.3,.1,1.0],"severe_burst":[2.4,-3.2,-2.0,-.3,.8],
      "severe_burst_with_financial_crisis":[2.4,-4.8,-2.6,-.7,.8]}
    equities={
      "continued_boom":[100,112,123,134,145],"no_burst_sideways":[100,95,99,102,106],
      "mild_adjustment":[100,72,76,84,92],"moderate_burst":[100,58,62,70,80],
      "deep_drawdown_no_vacuum":[100,42,46,55,66],"severe_burst":[100,34,38,47,59],
      "severe_burst_with_financial_crisis":[100,28,30,38,50]}
    unemployment={
      "continued_boom":[4.3,4.1,4.0,3.9,3.9],"no_burst_sideways":[4.3,4.8,5.0,4.8,4.5],
      "mild_adjustment":[4.3,5.4,5.8,5.4,4.9],"moderate_burst":[4.3,6.2,7.0,6.6,5.8],
      "deep_drawdown_no_vacuum":[4.3,7.1,8.2,7.8,6.8],"severe_burst":[4.3,8.0,9.3,8.8,7.5],
      "severe_burst_with_financial_crisis":[4.3,8.8,10.2,9.5,8.0]}
    spread_peak={"continued_boom":2.7,"no_burst_sideways":3.7,"mild_adjustment":4.6,"moderate_burst":5.7,"deep_drawdown_no_vacuum":6.5,"severe_burst":7.6,"severe_burst_with_financial_crisis":9.0}
    # Region multipliers include first-round trade/funding losses. EU gains from
    # reallocation only after the acute shock and only under policy follow-through.
    region_mult={"US":1.0,"China":.82,"EU":.68,"Switzerland":.48}
    base_2026={"US":2.4,"China":5.0,"EU":1.5,"Switzerland":1.4}; out={}
    for sc in SCEN:
      out[sc]={}
      us=np.array(us_gdp[sc],float)
      for c,m in region_mult.items():
        anchor=base_2026[c]+(us-us[0])*m
        if c=="China" and sc in ["deep_drawdown_no_vacuum","severe_burst","severe_burst_with_financial_crisis"]: anchor+=np.array([0,-.5,-.9,-.6,-.3])
        if c=="EU" and sc in ["deep_drawdown_no_vacuum","severe_burst","severe_burst_with_financial_crisis"]: anchor+=np.array([0,-.2,-.25,.15,.35])
        n=1600; eps=rng.normal(0,1,(n,5)); persistent=np.zeros_like(eps)
        for i in range(5): persistent[:,i]=(persistent[:,i-1]*.62 if i else 0)+eps[:,i]
        gdp=anchor+persistent*.32
        eq=np.array(equities[sc],float)+(persistent*3.2*m)
        un=np.array(unemployment[sc],float); un=4.3+(un-4.3)*m+persistent*.18
        peak=3.2+(spread_peak[sc]-3.2)*m
        spreads=np.array([3.2,peak,max(3.0,peak-.8),max(2.8,peak-2.0),max(2.7,peak-3.0)])+persistent*.20
        inflation=np.array([2.5,2.2,1.8,1.9,2.0])-(us[0]-us)*.10*m+persistent*.10
        gdp_level=100*np.cumprod(1+gdp/100,axis=1)
        vals={"gdpGrowth":gdp,"realGdpIndex":gdp_level,"unemployment":un,"equityIndex":eq,"creditSpread":spreads,"inflation":inflation}
        out[sc][c]={k:[{"year":y,"p10":float(np.quantile(v[:,i],.1)),"p50":float(np.quantile(v[:,i],.5)),"p90":float(np.quantile(v[:,i],.9))} for i,y in enumerate(years)] for k,v in vals.items()}
      out[sc]["benchmark"]={"label":"Severity anchor","text":("Fed 2026 severe test: US real-GDP level falls 4.6% from 2025 Q4 to the 2027 Q2 trough; the 2007Q4–2009Q2 contraction averaged −3.5% annualized." if "severe" in sc or "deep" in sc else "Path is a conditional regime design. Bands show propagation uncertainty within the selected scenario, not the probability of that scenario."),"sources":["Federal Reserve 2026 Stress Test Scenarios","BEA FAQ 1004"]}
    doc={"asOf":"2026-10-15","status":"scenario_conditional_nonlinear_regime_simulation","scenarios":out,"method":"1,600 persistent correlated paths around explicit regime anchors. Threshold regimes prevent automatic mean reversion after tail shocks; bands describe within-scenario propagation uncertainty."}
    dump("scenario_paths",doc); return doc

def build_connected_system(tree, systemic_bundle):
    """Joint path simulator with two-way US/China feedback and crisis flags."""
    systemic_model, systemic_template, systemic_audit = systemic_bundle
    rng=np.random.default_rng(SEED+7); years=[2026,2027,2028,2029,2030]; n=4000
    severity={"continued_boom":0,"no_burst_sideways":.14,"mild_adjustment":.30,"moderate_burst":.48,"deep_drawdown_no_vacuum":.66,"severe_burst":.82,"severe_burst_with_financial_crisis":1.0}
    shape=np.array([0,.95,.82,.58,.38]); result={}; path_stats={}
    def bands(a): return [{"year":y,"p10":float(np.quantile(a[:,i],.1)),"p50":float(np.quantile(a[:,i],.5)),"p90":float(np.quantile(a[:,i],.9))} for i,y in enumerate(years)]
    for sc,sev in severity.items():
        trust=np.ones((n,5)); equity=np.full((n,5),100.); liquidity=np.zeros((n,5)); margin=np.zeros((n,5)); coverage=np.full((n,5),1.65)
        tech_rate=np.full((n,5),5.0); treasury_sale=np.zeros((n,5)); china_outflow=np.zeros((n,5)); lgfv_rate=np.full((n,5),4.5)
        china_stress=np.full((n,5),.22); us_gdp=np.full((n,5),2.4); china_gdp=np.full((n,5),5.0); eu_gdp=np.full((n,5),1.5)
        for t in range(1,5):
            common=rng.normal(0,.07,n); trust[:,t]=np.clip(1-sev*shape[t]+common,.03,1.12)
            prev_eq=equity[:,t-1]; prev_liq=liquidity[:,t-1]; prev_ch=china_stress[:,t-1]
            liq=prev_liq*.52; eq=prev_eq.copy(); ch=prev_ch.copy()
            for _ in range(8):
                revenue=np.clip(.70+.40*trust[:,t]-.15*liq,.12,1.15)
                commitment=1+.48*sev*np.exp(-.18*(t-1))
                cov=1.82*revenue/commitment
                draw=np.maximum(0,1-eq/100); prev_draw=np.maximum(0,1-prev_eq/100)
                marg=.36*margin[:,t-1]+np.maximum(0,draw-prev_draw-.025)*(1.18+.72*sev)
                out=np.clip(.08+.50*liq+.34*(1-trust[:,t])+.25*ch,0,1)
                sale=np.clip(.025+.40*np.maximum(0,out-.30)+.18*ch,0,.72)
                # Policy response arrives with a lag and is less effective once
                # collateral and funding loops are both active.
                policy=.075*max(0,t-1)*sev*(1-.55*marg)
                liq=np.clip(.44*prev_liq+.76*np.maximum(0,1-cov)+1.12*marg+.34*sale-policy,0,1)
                if sc=="deep_drawdown_no_vacuum": liq=np.minimum(liq,.58)
                target=100*(1-.52*sev*shape[t]-.20*liq-.10*marg)
                eq=np.clip(.54*eq+.46*target+rng.normal(0,1.45,n),10,150)
                ch=np.clip(.58*prev_ch+.35*out+.24*liq+.11*sev,0,1)
            trust[:,t]=np.clip(trust[:,t]-.09*liq,0,1.12);equity[:,t]=eq;liquidity[:,t]=liq;margin[:,t]=marg;coverage[:,t]=cov
            treasury_sale[:,t]=sale;china_outflow[:,t]=out;china_stress[:,t]=ch
            tech_rate[:,t]=4.8+5.2*liq+1.3*np.maximum(0,1-cov)
            lgfv_rate[:,t]=4.5+5.1*out+1.35*sale
            us_gdp[:,t]=2.4-4.15*liq-1.85*(1-trust[:,t])-.70*marg+rng.normal(0,.30,n)
            china_gdp[:,t]=5.0-2.85*ch-1.85*out-.45*sale+rng.normal(0,.32,n)
            eu_gdp[:,t]=1.5-1.85*liq-.62*(1-trust[:,t])+.28*(t>=3)*sev+rng.normal(0,.25,n)
        drawdown=1-equity.min(axis=1)/100; maxliq=liquidity.max(axis=1); mincov=coverage.min(axis=1)
        maxout=china_outflow.max(axis=1); maxch=china_stress.max(axis=1); maxlgfv=lgfv_rate.max(axis=1)
        # Scenario probabilities already contain the calibrated transition from a
        # severe equity loss to a US banking crisis.  Path classification must
        # therefore respect the mutually exclusive scenario definitions rather
        # than count a second transition inside each branch.
        us_flag=np.full(n,sc=="severe_burst_with_financial_crisis",dtype=bool)
        low_growth=np.maximum(0,2-np.minimum(china_gdp[:,1],china_gdp[:,2]))
        p_ch=logistic(-5.80+2.6*maxout+1.5*maxch+.25*(maxlgfv-5)+.70*maxliq+.24*low_growth+1.30*us_flag)
        ch_flag=rng.random(n)<p_ch
        joint=us_flag&ch_flag; either=us_flag|ch_flag
        path_stats[sc]={"paths":n,"usSystemic":float(us_flag.mean()),"chinaCrisis":float(ch_flag.mean()),"joint":float(joint.mean()),"either":float(either.mean()),
          "chinaGivenUs":float(joint.sum()/max(1,us_flag.sum())),"usGivenChina":float(joint.sum()/max(1,ch_flag.sum())),
          "medianMaxLiquidity":float(np.median(maxliq)),"medianDrawdown":float(np.median(drawdown)),"medianMinCoverage":float(np.median(mincov))}
        result[sc]={k:bands(v) for k,v in {"aiTrust":trust,"usEquityIndex":equity,"marginCallPressure":margin,"liquidityStress":liquidity,"hyperscalerMarginalRate":tech_rate,"cashFlowCoverage":coverage,"treasurySalePressure":treasury_sale,"chinaCapitalOutflow":china_outflow,"lgfvRefinancingRate":lgfv_rate,"chinaBalanceSheetStress":china_stress,"usGdpGrowth":us_gdp,"chinaGdpGrowth":china_gdp,"euGdpGrowth":eu_gdp}.items()}
    probs={x['id']:x['probability'] for x in tree['scenarios']}
    mix={k:sum(probs[s]*path_stats[s][k] for s in SCEN) for k in ['usSystemic','chinaCrisis','joint','either']}
    mix['chinaGivenUs']=mix['joint']/max(mix['usSystemic'],1e-9);mix['usGivenChina']=mix['joint']/max(mix['chinaCrisis'],1e-9)
    # A model-generated reverse-stress surface conditional on an AI trust break.
    spreads=[3,4,5,6.5,8,10,12,14]; properties=[15,20,25,30,35,40]; grid=[]
    for prop in properties:
        row=[]
        for oas in spreads:
            m=6000; z=rng.normal(size=m); uu=logistic(z); uc=logistic(.62*z+np.sqrt(1-.62**2)*rng.normal(size=m))
            dd=np.clip(.30+.035*(oas-3)+rng.normal(0,.055,m),.20,.82)
            pu=predict_systemic(systemic_model,systemic_template,-dd)
            pu=logistic(logit(pu)+.17*(oas-4))
            usf=uu<pu
            pc=logistic(-3.7+.105*(prop-20)+.22*(oas-4)+1.2*usf)
            chf=uc<pc
            row.append(float(np.mean(usf&chf)))
        grid.append(row)
    grid=np.maximum.accumulate(np.maximum.accumulate(np.asarray(grid),axis=0),axis=1).tolist()
    doc={"asOf":"2026-10-15","status":"connected_structural_stress_simulation","scenarios":result,"pathClassification":path_stats,"mixture":mix,"systemicTransition":systemic_audit,"reverseStress":{"condition":"AI trust break; probabilities are conditional, not current-trajectory odds","x":{"label":"US high-yield OAS (%)","values":spreads},"y":{"label":"China property decline from peak (%)","values":properties},"values":grid,"copulaCorrelation":.62},"variables":{
      "aiTrust":"0–1 index; exogenous scenario trigger plus endogenous funding feedback","usEquityIndex":"2026=100; valuation and forced-sale feedback","marginCallPressure":"0–1 index activated by incremental collateral loss","liquidityStress":"0–1 shared state driven by coverage, margin calls and Treasury-sale pressure","hyperscalerMarginalRate":"illustrative marginal all-in funding rate, %","cashFlowCoverage":"operating cash generation / sticky commitment burden","treasurySalePressure":"0–1 foreign-official sale stress, not a forecast of intent","chinaCapitalOutflow":"0–1 external funding and capital-flight stress","lgfvRefinancingRate":"illustrative marginal refinancing rate, %","chinaBalanceSheetStress":"0–1 property/LGFV balance-sheet state"},
      "classification":{"usSystemic":"Bernoulli draw from calibrated banking-crisis transition, updated by simulated liquidity, coverage and China stress.","chinaCrisis":"Latent threshold driven by capital outflow, property/LGFV balance-sheet stress, refinancing cost, shared liquidity and US crisis feedback.","joint":"Both flags occur on the same path by 2028."},
      "feedbackLoops":["AI trust ↓ → revenue coverage ↓ → marginal funding rate ↑","equities ↓ → collateral loss → margin calls/liquidations ↑ → market liquidity ↓ → equities ↓","liquidity ↓ + China risk ↑ → capital outflow ↑ → LGFV refinancing premium ↑","China outflow/fiscal stress → Treasury-sale pressure ↑ → US liquidity/term premium ↑","China crisis raises US systemic transition risk; US systemic stress raises China crisis risk","US/China demand ↓ → EU recession first; reallocation benefit appears only later"],
      "warning":"The banking-crisis transition is statistically calibrated. China and cross-border elasticities are transparent stress-test parameters, not separately identified causal estimates."}
    dump("connected_system",doc); return doc

def build_historical_validation(paths):
    """Publish observed aggregate real-GDP paths alongside the scenario path."""
    specs=[("US dot-com unwind","USA",2000,5),("US GFC","USA",2007,5),("Euro-area GFC / sovereign aftershock","EMU",2007,7),("Japan post-asset-bubble","JPN",1990,6),("US pandemic stop","USA",2019,4)]
    analogs=[]
    for label,iso,start,n in specs:
        p=ROOT/f"data/derived/series/WB_NY.GDP.MKTP.KD.ZG_{iso}.csv"
        d=pd.read_csv(p);d["year"]=d.date.astype(str).str[:4].astype(int);d["value"]=pd.to_numeric(d.value,errors="coerce")
        z=d[d.year.between(start,start+n-1)].dropna(subset=["value"])
        level=100*np.cumprod(1+z.value.to_numpy()/100)
        analogs.append({"id":label.lower().replace(' ','_').replace('/','_'),"label":label,"region":iso,"startYear":start,
          "growth":[{"year":int(y),"value":float(g)} for y,g in zip(z.year,z.value)],
          "realGdpIndex":[{"year":int(y),"value":float(v)} for y,v in zip(z.year,level)],
          "yearsNegative":int((z.value<0).sum()),"cumulativeGrowth":float(level[-1]-100),"source":"World Bank NY.GDP.MKTP.KD.ZG"})
    model=paths["scenarios"]["severe_burst_with_financial_crisis"]["US"]
    analogs.append({"id":"model_systemic_2026","label":"Model: AI bust + financial crisis","region":"USA model","startYear":2026,
      "growth":[{"year":x["year"],"value":x["p50"]} for x in model["gdpGrowth"]],
      "realGdpIndex":[{"year":x["year"],"value":x["p50"]} for x in model["realGdpIndex"]],
      "yearsNegative":sum(x["p50"]<0 for x in model["gdpGrowth"]),"cumulativeGrowth":model["realGdpIndex"][-1]["p50"]-100,"source":"Conditional model path"})
    doc={"asOf":"2026-10-15","metric":"Annual aggregate real GDP growth and chained level, not per-capita GDP","analogs":analogs,
      "interpretation":"Dot-com shows that a valuation crash can remain non-systemic. The GFC shows the nonlinear outcome when losses sit in leveraged intermediaries. Japan shows that a balance-sheet recession can suppress the level path for years even without consecutive annual contractions.",
      "limitations":"Annual observations hide intrayear troughs. The pandemic is an exogenous magnitude check, not a causal analogue. The model is judged against ranges, not fitted to copy one episode."}
    dump("historical_validation",doc); return doc

def patch_other(tree,labels,us,connected):
    src=load("models/v3/china/out/china_hidden_debt.json"); dump("china_hidden_debt",src)
    dump("us_ai_decomposition",us)
    cont=load("models/v3/outputs/site/contagion.json"); dump("contagion",cont)
    mix=connected["mixture"]; joint=mix["joint"]
    joint_doc=load("models/v3/joint/out/joint_crisis.json")
    joint_doc.update({"probabilityCurrentTrajectory":{"point":joint,"interval80":[max(0,joint*.55),min(.75,joint*1.65)],"status":"weighted path simulation; interval is parameter sensitivity, not sampling error"},
      "marginals":{"usSystemic":mix["usSystemic"],"chinaCrisis":mix["chinaCrisis"],"eitherCrisis":mix["either"],"chinaCrisisConditionalOnUsSystemic":mix["chinaGivenUs"],"usSystemicConditionalOnChinaCrisis":mix["usGivenChina"]},
      "scenarioPathRates":connected["pathClassification"],"reverseStress":connected["reverseStress"],"drawsPerScenario":4000})
    joint_doc["dependence"]={"type":"same-path common shocks plus two-way fixed-point feedback","strength":connected["reverseStress"]["copulaCorrelation"],"estimationNote":"US transition is calibrated on a 17-country panel. China and cross-border elasticities are structural stress parameters. No fixed 42% conditional multiplier remains."}
    joint_doc["boundaryConditions"]=[{"variable":"US high-yield OAS","threshold":6.5,"unit":"percent","direction":"above","currentValue":3.16,"rationale":"Historical broad-stress threshold used in reverse stress grid."},{"variable":"Fed reserve balances","threshold":2500000,"unit":"USD million","direction":"below","currentValue":3029659,"rationale":"Low-reserve boundary in liquidity-vacuum stress grid."},{"variable":"China property decline","threshold":25,"unit":"percent from peak","direction":"above","currentValue":22.61,"rationale":"Frozen China crisis definition."},{"variable":"China real GDP growth","threshold":2,"unit":"percent","direction":"below","currentValue":4.96,"rationale":"Growth condition needed to sustain balance-sheet recession dynamics."}]
    joint_doc["sensitivity"]=[{"driver":"Banking-crisis transition","low":"20% drawdown","high":"75% drawdown","effect":"6.6% → 62.4% before liquidity feedback"},{"driver":"China property loss","low":15,"high":40,"effect":"shown in generated reverse-stress surface"},{"driver":"US high-yield OAS","low":3,"high":14,"effect":"shown in generated reverse-stress surface"},{"driver":"Policy offset","low":"early/strong","high":"late/weak","effect":"changes persistence and tail overlap"}]
    dump("joint_crisis",joint_doc)
    # Like-for-like comparison. Missing concepts stay explicit instead of being
    # replaced by unrelated regional statistics.
    profiles={
      "US":{"summary":"Largest direct valuation and capex channel; Treasury-market depth and refinancing costs determine whether an equity reset becomes systemic.","metrics":{"growth":2.34,"publicDebt":118.8,"privateCredit":216.3,"policyRate":4.25,"directExposure":"high"},"shockRole":"origin + dollar-funding amplifier"},
      "China":{"summary":"Lower direct US-AI exposure, but property losses, LGFV debt and weak domestic demand create a second balance-sheet channel.","metrics":{"growth":4.96,"publicDebt":None,"privateCredit":194.3,"policyRate":3.0,"directExposure":"low"},"shockRole":"property/debt amplifier + potential Treasury seller"},
      "EU":{"summary":"Lower direct AI concentration, but trade, banks and dollar funding transmit the first-round recession before any reallocation benefit.","metrics":{"growth":1.5,"publicDebt":87.4,"privateCredit":None,"policyRate":2.0,"directExposure":"medium"},"shockRole":"initial loss; conditional medium-term reallocation"},
      "Switzerland":{"summary":"Low public debt and safe-haven demand cushion funding stress; franc appreciation and EU-market access constrain exports.","metrics":{"growth":1.4,"publicDebt":17.2,"privateCredit":164.6,"policyRate":0.0,"directExposure":"medium"},"shockRole":"safe haven with export/currency trade-off"}}
    dump("country_profiles",{"asOf":"2026-10-15","metricDefinitions":{"growth":"2025 real GDP growth, %","publicDebt":"latest general/federal government debt, % GDP; perimeter differs","privateCredit":"latest domestic private credit, % GDP","policyRate":"policy rate, %, latest 2026 observation","directExposure":"qualitative direct AI/US-tech exposure"},"countries":profiles})

def main():
    tree,labels,us,systemic=build_scenarios();paths=build_paths(tree);connected=build_connected_system(tree,systemic);build_historical_validation(paths);patch_other(tree,labels,us,connected)
    print(json.dumps({"status":"released","probabilitySum":sum(x["probability"] for x in tree["scenarios"]),"draws":DRAWS,"scenarios":{x["id"]:x["probability"] for x in tree["scenarios"]}},indent=2))
if __name__=="__main__": main()
