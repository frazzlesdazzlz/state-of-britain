import json, urllib.request, urllib.parse, datetime, re, html as html_lib, csv, io
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data.json"; HISTORY=ROOT/"data/history.json"
def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":"State-of-Britain/1.1"})
 with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
def ons_series(cdid):
 search=get("https://api.beta.ons.gov.uk/v1/search?content_type=timeseries&cdids="+cdid)
 items=search.get("items",[])
 if not items: raise ValueError("ONS series not found")
 uri=items[0].get("uri")
 if not uri: raise ValueError("ONS series URI missing")
 return get("https://api.beta.ons.gov.uk/v1/data?uri="+urllib.parse.quote(uri,safe="/"))

def latest_from_series(cdid):
 j=ons_series(cdid)
 # v1 data responses can expose observations under months or observations.
 rows=j.get("months") or j.get("observations") or j.get("data") or []
 if isinstance(rows,dict): rows=rows.get("months") or rows.get("observations") or rows.get("items") or []
 if not rows: raise ValueError("ONS observations missing")
 x=rows[-1]
 value=x.get("value") if isinstance(x,dict) else None
 period=(x.get("date") or x.get("label") or x.get("time") or "latest") if isinstance(x,dict) else "latest"
 return float(str(value).replace(",","")),period

def csv_rows(url):
 req=urllib.request.Request(url,headers={"User-Agent":"State-of-Britain/1.3"})
 with urllib.request.urlopen(req,timeout=25) as r:
  return list(csv.DictReader(io.StringIO(r.read().decode("utf-8-sig","ignore"))))

def latest_gdp_structured():
 # ONS MGDP current-edition CSV: official monthly GDP time-series dataset.
 url="https://www.ons.gov.uk/file?uri=/economy/grossdomesticproductgdp/datasets/gdpmonthlyestimateuktimeseriesdataset/current/gdpmonthlyestimateuktimeseriesdataset.csv"
 rows=csv_rows(url)
 # Find rows describing whole-economy GDP growth, then take latest monthly and 3m-on-3m observations.
 def findrow(words):
  for r in rows:
   blob=" ".join(str(v) for v in r.values()).lower()
   if all(w in blob for w in words): return r
  raise ValueError("GDP structured series not found")
 def latest_numeric(r):
  vals=[]
  for k,v in r.items():
   try:
    n=float(str(v).replace(",","").strip())
    if re.search(r"20[0-9]{2}",str(k)): vals.append((k,n))
   except: pass
  if not vals: raise ValueError("GDP structured observations missing")
  return vals[-1]
 monthly=findrow(["gross domestic product","month on previous month"])
 three=findrow(["gross domestic product","3 months on previous 3 months"])
 mp,mv=latest_numeric(monthly); tp,tv=latest_numeric(three)
 if not (-30 <= mv <= 30 and -30 <= tv <= 30): raise ValueError("GDP structured sanity check")
 return mv,mp,tv,tp,url

def page_text(url):
 req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 State-of-Britain/1.2","Accept":"text/html"})
 last=None
 for attempt in range(3):
  try:
   with urllib.request.urlopen(req,timeout=25) as r:
    raw=r.read().decode("utf-8","ignore")
   break
  except Exception as e:
   last=e
   if attempt==2: raise
   import time; time.sleep(2*(attempt+1))
 raw=re.sub(r"<script\b[^>]*>.*?</script>"," ",raw,flags=re.I|re.S)
 raw=re.sub(r"<style\b[^>]*>.*?</style>"," ",raw,flags=re.I|re.S)
 raw=re.sub(r"<[^>]+>"," ",raw)
 return re.sub(r"\s+"," ",html_lib.unescape(raw)).strip()

def latest_cpi_bulletin():
 url="https://www.ons.gov.uk/economy/inflationandpriceindices/bulletins/consumerpriceinflation/latest"
 t=page_text(url)
 m=re.search(r"Consumer Prices Index \\(CPI\\) rose by ([0-9.]+)% in the 12 months to ([A-Za-z]+ 20[0-9]{2}), up from ([0-9.]+)%",t,re.I)
 if not m: raise ValueError("CPI bulletin pattern not found")
 v=float(m.group(1))
 if not (-10 <= v <= 30): raise ValueError("CPI failed sanity check")
 return v,m.group(2),float(m.group(3)),url

def latest_monthly_borrowing_bulletin():
 url="https://www.ons.gov.uk/economy/governmentpublicsectorandtaxes/publicsectorfinance/bulletins/publicsectorfinances/latest"
 t=page_text(url)
 m=re.search(r"Borrowing.{0,120}?was £([0-9.]+) billion in ([A-Za-z]+ 20[0-9]{2})",t,re.I)
 if not m: raise ValueError("monthly borrowing bulletin pattern not found")
 v=float(m.group(1))
 if not (0 <= v <= 100): raise ValueError("monthly borrowing failed sanity check")
 return v,m.group(2),url

def latest_gdp_bulletin():
 url="https://www.ons.gov.uk/economy/grossdomesticproductgdp/bulletins/gdpmonthlyestimateuk/latest"
 t=page_text(url)
 month=re.search(r"Monthly GDP grew by ([0-9.]+)% in ([A-Za-z]+ 20[0-9]{2})",t,re.I)
 three=re.search(r"Real gross domestic product \\(GDP\\) grew by ([0-9.]+)%.{0,120}?three months to ([A-Za-z]+ 20[0-9]{2})",t,re.I)
 if not month or not three: raise ValueError("GDP bulletin pattern not found")
 mv=float(month.group(1)); tv=float(three.group(1))
 if not (-30 <= mv <= 30 and -30 <= tv <= 30): raise ValueError("GDP failed sanity check")
 return mv,month.group(2),tv,three.group(2),url

def latest_labour_bulletin():
 url="https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/bulletins/employmentintheuk/latest"
 t=page_text(url)
 period=re.search(r"latest quarter \\(([A-Za-z]+ to [A-Za-z]+ 20[0-9]{2})\\)",t,re.I)
 emp=re.search(r"employment rate.{0,260}?at ([0-9.]+)%",t,re.I)
 unemp=re.search(r"unemployment rate.{0,260}?at ([0-9.]+)%",t,re.I)
 inac=re.search(r"economic inactivity rate.{0,260}?at ([0-9.]+)%",t,re.I)
 if not period or not emp or not unemp or not inac: raise ValueError("labour bulletin pattern not found")
 ev=float(emp.group(1)); uv=float(unemp.group(1)); iv=float(inac.group(1))
 if not (60 <= ev <= 90 and 0 <= uv <= 15 and 10 <= iv <= 35): raise ValueError("labour values failed sanity check")
 return ev,period.group(1),uv,period.group(1),iv,period.group(1),None,None,url

def latest_pay_bulletin():
 url="https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/bulletins/averageweeklyearningsingreatbritain/latest"
 html=page_text(url)
 weekly=re.search(r"estimated at £[0-9,]+ for total earnings and £([0-9,]+) for regular earnings in ([A-Za-z]+ 20[0-9]{2})",html,re.I)
 real=re.search(r"real terms.*?annual regular pay growth.*?([0-9.]+)% in ([A-Za-z]+ to [A-Za-z]+ 20[0-9]{2})",html,re.I|re.S)
 if not weekly or not real: raise ValueError("pay bulletin pattern not found")
 return int(weekly.group(1).replace(",","")),weekly.group(2),float(real.group(1)),real.group(2),url

def latest_housing_bulletin():
 url="https://www.ons.gov.uk/economy/inflationandpriceindices/bulletins/privaterentandhousepricesuk/latest"
 html=page_text(url)
 rent=re.search(r"Average UK monthly private rent increased by ([0-9.]+)%, to £([0-9,]+), in the 12 months to ([A-Za-z]+ 20[0-9]{2})",html,re.I)
 house=re.search(r"Average UK house prices increased by ([0-9.]+)%, to £([0-9,]+), in the 12 months to ([A-Za-z]+ 20[0-9]{2})",html,re.I)
 if not rent or not house: raise ValueError("housing bulletin pattern not found")
 return int(house.group(2).replace(",","")),float(house.group(1)),house.group(3),int(rent.group(2).replace(",","")),float(rent.group(1)),rent.group(3),url

def latest_bank_rate():
 url="https://www.bankofengland.co.uk/monetary-policy/the-interest-rate-bank-rate"
 html=page_text(url)
 rate=re.search(r"Current Bank Rate\s*([0-9.]+)%",html,re.I)
 nxt=re.search(r"Next due:\s*([0-9]{1,2} [A-Za-z]+ 20[0-9]{2})",html,re.I)
 if not rate: raise ValueError("Bank Rate pattern not found")
 return float(rate.group(1)),nxt.group(1) if nxt else "next MPC decision",url

def latest_public_finances_bulletin():
 url="https://www.ons.gov.uk/economy/governmentpublicsectorandtaxes/publicsectorfinance/bulletins/publicsectorfinances/latest"
 t=page_text(url)
 def val(pattern):
  m=re.search(pattern,t,re.I|re.S)
  if not m: raise ValueError("public finance pattern not found")
  return float(m.group(1).replace(",",""))
 debt=val(r"net debt.{0,220}?estimated at £([0-9,.]+) billion")
 dgdp=val(r"Debt at the end of [A-Za-z]+ 20[0-9]{2} was equivalent to ([0-9.]+)% of GDP")
 fy=val(r"Borrowing was £([0-9.]+) billion in the financial year \\(FY\\) to")
 receipts=val(r"gap between £([0-9.]+) billion in current receipts and £[0-9.]+ billion in current spending")
 expenditure=val(r"Central government total expenditure\\s+([0-9.]+)")
 interest=val(r"debt interest payable.{0,260}?£([0-9.]+) billion")
 if not (1000 <= debt <= 5000 and 20 <= dgdp <= 200 and 0 <= fy <= 500 and 100 <= receipts <= 1000 and 100 <= expenditure <= 1200 and 0 <= interest <= 100):
  raise ValueError("public finance values failed sanity check")
 return debt,dgdp,fy,receipts,expenditure,interest,url

def item(d,id):
 for g in d["groups"]:
  for x in g.get("items",[]):
   if x["id"]==id:return x
def setv(d,id,display,period,source,url,now,changes):
 x=item(d,id)
 if not x:return
 old=x.get("display")
 x.update(display=display,period=period,source=source,source_url=url,retrieved_at=now)
 def norm(v):
  z=str(v).replace(",","").strip()
  return z[1:] if z.startswith("+") else z
 if norm(old)!=norm(display):changes.append({"id":id,"from":old,"to":display,"at":now})
def main():
 d=json.loads(DATA.read_text()); now=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(); changes=[]; errors=[]
 collectors=[]
 try:
  cv,cp=latest_from_series("D7G7")
  if not (-10 <= cv <= 30): raise ValueError("CPI series failed sanity check")
  curl="https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/d7g7/mm23"
  setv(d,"cpi",f"{cv:.1f}%",cp,"ONS",curl,now,changes)
 except Exception as e: errors.append("cpi:"+type(e).__name__+":"+str(e)[:80])
 try:
  mv,mp,tv,tp,gurl=latest_gdp_structured()
  setv(d,"gdp_month",f"{mv:+.1f}%",mp,"ONS",gurl,now,changes)
  setv(d,"gdp_3m",f"{tv:+.1f}%",tp,"ONS",gurl,now,changes)
 except Exception as e: errors.append("gdp:"+type(e).__name__+":"+str(e)[:80])
 try:
  bv,bp,burl=latest_monthly_borrowing_bulletin()
  setv(d,"monthly_borrowing",f"£{bv:.1f}bn",bp,"ONS",burl,now,changes)
 except Exception as e: errors.append("monthly_borrowing:"+type(e).__name__)

 # Structured migration pending; keep last-known-good values for this dataset.

 # Structured migration pending; keep last-known-good values for this dataset.
 try:
  wv,wp,rv,rp,purl=latest_pay_bulletin()
  setv(d,"pay",f"£{wv:,}",wp+" before tax","ONS",purl,now,changes)
  setv(d,"real_pay",f"{rv:+.1f}%",rp+" y/y, CPIH-adjusted","ONS",purl,now,changes)
 except Exception as e: errors.append("pay:"+type(e).__name__)

 # Structured migration pending; keep last-known-good values for this dataset.
 try:
  br,bnext,burl=latest_bank_rate()
  setv(d,"bank_rate",f"{br:.2f}%","current Bank Rate","Bank of England",burl,now,changes)
  bx=item(d,"bank_rate")
  if bx: bx["comparison"]="Next decision "+bnext
 except Exception as e: errors.append("bank_rate:"+type(e).__name__)

 # Structured migration pending; keep last-known-good values for this dataset.
 for id,s,ds,fmt,url in collectors:
  try:
   v,p=latest_month(s,ds); setv(d,id,fmt(v),p,"ONS",url,now,changes)
  except Exception as e: errors.append(id+":"+type(e).__name__)
 d["recent_changes"]=changes
 d["last_checked"]=now
 d["changed_count"]=len(changes)
 d["collector_status"]="ok" if not errors else "; ".join(errors)
 DATA.write_text(json.dumps(d,indent=2)+"\n")
 try:h=json.loads(HISTORY.read_text())
 except:h=[]
 h.append({"checked_at":now,"changes":changes,"errors":errors}); HISTORY.write_text(json.dumps(h[-1000:],indent=2)+"\n")
if __name__=="__main__":main()
