import os
import sys
import traceback
import subprocess
import logging
import json
import fcntl
import time

module_logger = logging.getLogger(__name__)
def run(cmd,logger=None,
        stop_on_error=True,
        dry_run=False,
        folder='.',
        pipe_output=False):
    logger = logger or module_logger
    logger_in  = logging.getLogger(logger.name + '.' + __name__.split('.')[-1:][0] + '.input')
    logger_out = logging.getLogger(logger.name + '.' + __name__.split('.')[-1:][0] + '.output')
    logger_err = logging.getLogger(logger.name + '.' + __name__.split('.')[-1:][0] + '.error')
    if not cmd :
        logger.warning("skipping empty command")
        return (0, '','')
    logger_in.info("> "+' '.join(cmd))
    # logger.debug("PATH: " + os.environ['PATH'])
    # print("running-->"+' '.join(cmd))
    if not dry_run :
        myprocess = subprocess.Popen(cmd, cwd=folder,stdout=subprocess.PIPE,stderr=subprocess.PIPE, env=os.environ, bufsize=1, universal_newlines=True)
        if pipe_output:
            # for f in [myprocess.stdout, myprocess.stderr]:
            #     fd = f.fileno()
            #     fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            #     fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
            out_buf=''
            err_buf=''
            while myprocess.poll() is None:
                #print("in while")
                while True:
                    try:
                        next_out_line = myprocess.stdout.readline()
                    except:
                        module_logger.warning("##################missing out")
                        # sys.sleep(1)
                        next_out_line = ''
                        time.sleep(1)
                    if next_out_line != '':
                        out_buf += next_out_line
                        # ligth gray color:
                        logger_out.info(next_out_line.rstrip())
                    else:
                        break
                while True:
                    try:
                        next_err_line = myprocess.stderr.readline()
                    except:
                        module_logger.warning("##################missing err")
                        next_err_line = ''
                        time.sleep(1)
                    if next_err_line != '':
                        err_buf += next_err_line
                        logger_err.warning(next_err_line.rstrip())
                    else:
                        break


            # print("exited while")

        else:
            out_buf,err_buf = myprocess.communicate()
        myprocess.wait()
        ret = myprocess.returncode
        if ret:
            #print("ERROR:",ret,"Exiting")
            logger.error("ERROR CODE : " + str(ret) + '\n' + err_buf +'\nexecuting ->' + ' '.join(cmd) + '\n' + str(traceback.format_stack()))
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
        logger.info("sourcing-->"+ source+ "<-")
        dump = sys.executable + ' -c "import os, json; print(json.dumps(dict(os.environ)))"'
        pipe = subprocess.Popen(['/bin/bash', '-c', '%s && %s' %(source,dump)], stdout=subprocess.PIPE)
        env = json.loads(pipe.stdout.read().decode('utf-8'))
        os.environ = env
    else:
        logger.warning("### NON EXISTING "+ sourcefile)
