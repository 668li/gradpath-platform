import subprocess, os
base='/app/app/api/'
files=['bookmarks.py','notifications.py','rag_search.py','admission_predict.py','community_rating.py']
for f in files:
    p=base+f
    if not os.path.exists(p):
        print(f'=== {f}: NOT FOUND ===')
        continue
    print(f'=== {f} ===')
    out=subprocess.run(['grep','-nE','@router\.(get|post|put|delete)|prefix=','p],capture_output=True,text=True).stdout
    print(out[:800])
    print()
