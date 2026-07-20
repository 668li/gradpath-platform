import subprocess
print(subprocess.run(['cat','/app/app/services/comment_service.py'],capture_output=True,text=True).stdout[:2000])
