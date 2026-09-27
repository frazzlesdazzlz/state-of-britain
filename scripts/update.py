import json, urllib.request, datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data.json"
HISTORY=ROOT/"data/history.json"

# First production collector: ONS public-sector borrowing.
# ONS series -J5II, dataset PUSF. More adapters are added only after validation.
URL="https://api.ons.gov.uk/timeseries/-J5II/dataset/PUSF/data"

def fetch_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":"State-of-Britain/1.0"})
    with urllib.request.urlopen(req,timeout=20) as r:
        return json.load(r)

def main():
    d=json.loads(DATA.read_text())
    now=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    changes=[]
    try:
        raw=fetch_json(URL)
        months=raw.get("months",[])
        if months:
            latest=months[-1]
            value=float(str(latest["value"]).replace(",",""))/1000
            period=latest.get("date",latest.get("label","latest"))
            for g in d["groups"]:
                for x in g.get("items",[]):
                    if x["id"]=="monthly_borrowing":
                        old=x["display"]
                        new=f"£{value:.1f}bn"
                        x["display"]=new
                        x["period"]=period
                        x["source"]="ONS"
                        x["source_url"]="https://www.ons.gov.uk/economy/governmentpublicsectorandtaxes/publicsectorfinance"
                        x["retrieved_at"]=now
                        if new!=old: changes.append({"id":x["id"],"from":old,"to":new,"at":now})
    except Exception as e:
        d["collector_status"]="ONS collector error: "+type(e).__name__
    d["last_checked"]=now
    d["changed_count"]=len(changes)
    DATA.write_text(json.dumps(d,indent=2)+"\n")
    try: hist=json.loads(HISTORY.read_text())
    except Exception: hist=[]
    hist.append({"checked_at":now,"changes":changes})
    HISTORY.write_text(json.dumps(hist[-1000:],indent=2)+"\n")

if __name__=="__main__": main()
