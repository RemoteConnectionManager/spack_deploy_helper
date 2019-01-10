import os
import sys
import subprocess
import logging
import json

def run(cmd,logger=None,stop_on_error=True,dry_run=False,folder='.'):
    logger = logger or logging.getLogger(__name__)
    if not cmd :
        logger.warning("skipping empty command")
        return (0, '','')
    logger.info("running-->"+' '.join(cmd)+"<-\n"+os.environ['PATH'])
    print("running-->"+' '.join(cmd))
    if not dry_run :
        myprocess = subprocess.Popen(cmd, cwd=folder,stdout=subprocess.PIPE,stderr=subprocess.PIPE, env=os.environ)
        stdout,stderr = myprocess.communicate()
        myprocess.wait()
        ret = myprocess.returncode
        if ret:
            #print("ERROR:",ret,"Exiting")
            logger.error("ERROR CODE : " + str(ret) + '\n'+stderr+'\nExit...\n')
            if stop_on_error :
                sys.exit()
        return (ret,stdout,stderr)

    else:
        logger.info("DRY RUN... nothing done")
        return (0, '','')


def source(sourcefile,logger=None):
    logger = logger or logging.getLogger(__name__)
    if os.path.exists(sourcefile) :
        source = 'source '+ sourcefile
        logger.info("spurcing-->"+ source+ "<-")
        dump = sys.executable + ' -c "import os, json; print(json.dumps(dict(os.environ)))"'
        pipe = subprocess.Popen(['/bin/bash', '-c', '%s && %s' %(source,dump)], stdout=subprocess.PIPE)
        env = json.loads(pipe.stdout.read().decode('utf-8'))
        os.environ = env
    else:
        logger.warning("### NON EXISTING "+ sourcefile)
