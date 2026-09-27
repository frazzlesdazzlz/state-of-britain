import json, urllib.request, datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"data.json"; HISTORY=ROOT/"data/history.json"
def get(url):
 req=urllib.request.Request(url,headers={"User-Agent":"State-of-Britain/1.1"})
 with urllib.request.urlopen(req,timeout=25) as r:return json.load(r)
def latest_month(series,dataset):
 j=get(f"https://api.ons.gov.uk/timeseries/{series}/dataset/{dataset}/data")
 rows=j.get("months",[]); x=rows[-1]; return float(str(x["value"]).replace(",","")),x.get("date",x.get("label","latest"))
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
  ("monthly_borrowing","-J5II","PUSF",lambda v:f"£{v/1000:.1f}bn","https://www.ons.gov.uk/economy/governmentpublicsectorandtaxes/publicsectorfinance")
 ]
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
