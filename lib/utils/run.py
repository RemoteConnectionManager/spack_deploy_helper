import os
import sys
import subprocess
import logging
import json
import fcntl

def run(cmd,logger=None,
        stop_on_error=True,
        dry_run=False,
        folder='.',
        pipe_output=False):
    logger = logger or logging.getLogger(__name__)
    if not cmd :
        logger.warning("skipping empty command")
        return (0, '','')
    logger.info("running: "+' '.join(cmd))
    # logger.debug("PATH: " + os.environ['PATH'])
    # print("running-->"+' '.join(cmd))
    if not dry_run :
        myprocess = subprocess.Popen(cmd, cwd=folder,stdout=subprocess.PIPE,stderr=subprocess.PIPE, env=os.environ)
        if pipe_output:
            #for f in [myprocess.stdout, myprocess.stderr]:
            #    fd = f.fileno()
            #    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            #    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            out_buf=''
            err_buf=''
            loop_var = True
            ret=0
            while loop_var:
                #print("in while")
                try:
                    next_out_line = myprocess.stdout.readline()
                    if next_out_line != '':
                        out_buf += next_out_line
                        logger.info(next_out_line.rstrip())
                except:
                    print("missing out")
                    #sys.sleep(1)
                    next_out_line=''
                try:
                    next_err_line = myprocess.stderr.readline()
                    if next_err_line != '':
                        err_buf += next_err_line
                        logger.warning(next_err_line.rstrip())
                    loop_var=True
                except:
                    print("missing err")
                    next_err_line=''

                #ret = myprocess.returncode
                loop_var = next_err_line != '' or next_out_line != '' or myprocess.poll() is None
            print("exited while")

        else:
            out_buf,err_buf = myprocess.communicate()
            myprocess.wait()
            ret = myprocess.returncode
        if ret:
            #print("ERROR:",ret,"Exiting")
            logger.error("ERROR CODE : " + str(ret) + '\n'+stderr+'\nExit...\n')
            if stop_on_error :
                sys.exit()
        # print("############################",stdout)
        return (ret,out_buf,err_buf)

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
