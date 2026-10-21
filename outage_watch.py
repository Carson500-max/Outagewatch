import json,os,sys,time,urllib.request as U
F="https://services.arcgis.com/BLN4oKB0N1YSgvY8/ArcGIS/rest/services/Power_Outages_(View)/FeatureServer/0/query?outFields=*&outSR=4326&f=json&where=UtilityCompany%3D%27SDGE%27+AND+County%3D%27SAN+DIEGO%27+AND+OutageType%3C%3E%27Planned%27"
def tell(t,m,p,o={}):
 d={"topic":os.environ["NTFY_TOPIC"],"title":t,"message":m,"priority":p}
 if o.get("y"):d["click"]=f"https://www.google.com/maps/dir/?api=1&destination={o['y']},{o['x']}"
 print(t,m)
 try:U.urlopen(U.Request("https://ntfy.sh",json.dumps(d).encode(),{"Content-Type":"application/json"}),timeout=15)
 except Exception as e:print(e)
def hr(o):return(time.time()*1000-(o["s"] or 0))/3.6e6
def big(o):return o["k"]>=200 or o["k"]*hr(o)>=300
if "--test" in sys.argv:tell("BIG one back on (TEST)","340 customers were out 3 hrs. Go knock.",5,{"y":33.12,"x":-117.09});sys.exit()
cur={}
for f in json.load(U.urlopen(U.Request(F,headers={"User-Agent":"outage-watch"}),timeout=30))["features"]:
 a=f["attributes"]
 if a.get("OutageStatus")!="Restored":cur[str(a["IncidentId"])]=dict(f.get("geometry") or {},n=a.get("ImpactedCustomers") or 0,s=a.get("StartDate"))
try:st=json.load(open("state.json"));first=0
except Exception:st={};first=1
if first:
 st={i:dict(v,k=v["n"],b=0,m=0) for i,v in cur.items()}
 tell("Outage Watch is live",f"Watching {len(cur)} outages.",3)
else:
 for i,v in cur.items():
  if i not in st:
   o=st[i]=dict(v,k=v["n"],b=0,m=0);o["b"]=big(o)
   tell("BIG OUTAGE" if o["b"] else "Outage",f"{v['n']} customers out.",4 if o["b"] else 3,o)
  else:
   o=st[i];o.update(v,k=max(o["k"],v["n"]),m=0)
   if not o["b"] and big(o):o["b"]=1;tell("Now a BIG outage",f"{o['k']} customers out {hr(o):.1f} hrs.",4,o)
 for i in list(st):
  if i in cur:continue
  o=st[i];o["m"]+=1
  if o["m"]>=2:
   del st[i]
   if o["b"] or hr(o)>=0.5:tell("BIG one back on" if big(o) else "Power back",f"{o['k']} customers were out {hr(o):.1f} hrs. Go knock.",5 if big(o) else 4,o)
json.dump(st,open("state.json","w"))
print("ok",len(st))
