import json, urllib.request, datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data.json"; HISTORY=ROOT/"data/history.json"
def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":"State-of-Britain/1.1"})
 with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
def latest_month(series,dataset):
 j=get(f"https://api.ons.gov.uk/timeseries/{series}/dataset/{dataset}/data")
 rows=j.get("months",[]); x=rows[-1]; return float(str(x["value"]).replace(",","")),x.get("date",x.get("label","latest"))
def latest_gdp_bulletin():
 url="https://www.ons.gov.uk/economy/grossdomesticproductgdp/bulletins/gdpmonthlyestimateuk/latest"
 req=urllib.request.Request(url,headers={"User-Agent":"State-of-Britain/1.1"})
 with urllib.request.urlopen(req,timeout=25) as r:
  html=r.read().decode("utf-8","ignore")
 import re
 month=re.search(r"Monthly GDP (?:is estimated to have )?(?:grown|increased) by ([0-9.]+)% in ([A-Za-z]+ 20[0-9]{2})",html,re.I)
 three=re.search(r"Real gross domestic product \(GDP\) (?:is estimated to have )?(?:grown|increased) by ([0-9.]+)% in the three months to ([A-Za-z]+ 20[0-9]{2})",html,re.I)
 if not month or not three: raise ValueError("GDP bulletin pattern not found")
 return float(month.group(1)),month.group(2),float(three.group(1)),three.group(2),url

def latest_labour_bulletin():
 url="https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/bulletins/uklabourmarket/latest"
 req=urllib.request.Request(url,headers={"User-Agent":"State-of-Britain/1.1"})
 with urllib.request.urlopen(req,timeout=25) as r:
  html=r.read().decode("utf-8","ignore")
 import re
 def grab(pattern):
  m=re.search(pattern,html,re.I|re.S)
  if not m: raise ValueError("labour bulletin pattern not found")
  return m
 emp=grab(r"employment rate.*?estimated at\s*([0-9.]+)%\s*for\s*([A-Za-z]+ to [A-Za-z]+ 20[0-9]{2})")
 unemp=grab(r"unemployment rate.*?estimated at\s*([0-9.]+)%\s*in\s*([A-Za-z]+ to [A-Za-z]+ 20[0-9]{2})")
 inac=grab(r"economic inactivity rate.*?estimated at\s*([0-9.]+)%\s*in\s*([A-Za-z]+ to [A-Za-z]+ 20[0-9]{2})")
 payroll=grab(r"early estimate of payrolled employees for\s*([A-Za-z]+ 20[0-9]{2}).*?to\s*([0-9.]+) million")
 return (float(emp.group(1)),emp.group(2),float(unemp.group(1)),unemp.group(2),
         float(inac.group(1)),inac.group(2),float(payroll.group(2)),payroll.group(1),url)

def item(d,id):
 for g in d["groups"]:
  for x in g.get("items",[]):
   if x["id"]==id:return x
def setv(d,id,display,period,source,url,now,changes):
 x=item(d,id)
 if not x:return
 old=x.get("display")
 x.update(display=display,period=period,source=source,source_url=url,retrieved_at=now)
 if old!=display:changes.append({"id":id,"from":old,"to":display,"at":now})
def main():
 d=json.loads(DATA.read_text()); now=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(); changes=[]; errors=[]
 collectors=[
  ("cpi","D7G7","MM23",lambda v:f"{v:.1f}%","https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/d7g7/mm23"),
  ("monthly_borrowing","J5II","PUSF",lambda v:f"£{abs(v)/1000:.1f}bn","https://www.ons.gov.uk/economy/governmentpublicsectorandtaxes/publicsectorfinance")
 ]
 try:
  mv,mp,tv,tp,gurl=latest_gdp_bulletin()
  setv(d,"gdp_month",f"{mv:.1f}%",mp,"ONS",gurl,now,changes)
  setv(d,"gdp_3m",f"{tv:.1f}%",f"3 months to {tp}","ONS",gurl,now,changes)
 except Exception as e: errors.append("gdp:"+type(e).__name__)
 try:
  ev,ep,uv,up,iv,ip,pv,pp,lurl=latest_labour_bulletin()
  setv(d,"employment",f"{ev:.1f}%",ep,"ONS",lurl,now,changes)
  setv(d,"unemployment",f"{uv:.1f}%",up,"ONS",lurl,now,changes)
  setv(d,"inactivity",f"{iv:.1f}%",ip,"ONS",lurl,now,changes)
  setv(d,"payrolled",f"{pv:.1f}m",pp+" early estimate","ONS / HMRC PAYE RTI",lurl,now,changes)
 except Exception as e: errors.append("labour:"+type(e).__name__)
 for id,s,ds,fmt,url in collectors:
  try:
   v,p=latest_month(s,ds); setv(d,id,fmt(v),p,"ONS",url,now,changes)
  except Exception as e: errors.append(id+":"+type(e).__name__)
 d["last_checked"]=now; d["changed_count"]=len(changes); d["collector_status"]="ok" if not errors else "; ".join(errors)
 DATA.write_text(json.dumps(d,indent=2)+"\n")
 try:h=json.loads(HISTORY.read_text())
 except:h=[]
 h.append({"checked_at":now,"changes":changes,"errors":errors}); HISTORY.write_text(json.dumps(h[-1000:],indent=2)+"\n")
if __name__=="__main__":main()
