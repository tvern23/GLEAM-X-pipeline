#! /bin/bash

usage()
{
echo "obs_apply_cal.sh [-p project] [-d dep] [-q queue] [-c calid] [-t] [-n] obsnum
  -p project  : project, no default
  -d dep      : job number for dependency (afterok)
  -q queue    : job queue, default=gpuq
  -c calid    : obsid for calibrator.
                project/calid/calid_*_solutions.bin will be used
                to calibrate if it exists, otherwise job will fail.
  -t          : test. Don't submit job, just make the batch file
                and then return the submission command
  obsnum      : the obsid to process" 1>&2;
exit 1;
}

# Supercomputer options
if [[ "${HOST:0:4}" == "zeus" ]]
then
    computer="zeus"
    account="mwasci"
    standardq="workq"
#    absmem=60
#    standardq="gpuq"
#    absmem=30
elif [[ "${HOST:0:4}" == "magn" ]]
then
    computer="magnus"
    account="pawsey0272"
    standardq="workq"
#    absmem=60
elif [[ "${HOST:0:4}" == "athe" ]]
then
    computer="athena"
    account="pawsey0272"
    standardq="gpuq"
#    absmem=30 # Check this
fi

#initial variables
scratch=/astro
dep=
queue="-p $standardq"
calid=
tst=

# parse args and set options
while getopts ':td:q:c:p:' OPTION
do
    case "$OPTION" in
    d)
        dep=${OPTARG}
        ;;
	c)
	    calid=${OPTARG}
	    ;;
	q)
	    queue="-p ${OPTARG}"
	    ;;
    p)
        project=${OPTARG}
        ;;
    t)
        tst=1
        ;;
    ? | : | h)
        usage
        ;;
  esac
done

# set the obsid to be the first non option
shift  "$(($OPTIND -1))"
obsnum=$1

set -uo pipefail
# if obsid is empty then just print help

if [[ -z ${obsnum} ]]
then
    usage
fi

if [[ ! -z ${dep} ]]
then
    dep="--dependency=afterok:${dep}"
fi

# Set directories
dbdir="/group/mwasci/$USER/GLEAM-X-pipeline/"
base="$scratch/mwasci/$USER/$project/"

if [[ $? != 0 ]]
then
    echo "Could not find calibrator file"
    echo "looked for latest of: ${base}/${calid}/${calid}*solutions*.bin"
    exit 1
fi


script="${dbdir}queue/apply_cal_${obsnum}.sh"

cd $dbdir/bin

cat apply_cal.tmpl | sed -e "s:OBSNUM:${obsnum}:g" \
                                     -e "s:BASEDIR:${base}:g" \
                                     -e "s:HOST:${computer}:g" \
                                     -e "s:STANDARDQ:${standardq}:g" \
                                     -e "s:ACCOUNT:${account}:g" \
                                     -e "s:CALID:${calid}:g"  > ${script}

output="${dbdir}queue/logs/apply_cal_${obsnum}.o%A"
error="${dbdir}queue/logs/apply_cal_${obsnum}.e%A"

sub="sbatch --begin=now+15 --output=${output} --error=${error} ${dep} ${queue} ${script}"
if [[ ! -z ${tst} ]]
then
    echo "script is ${script}"
    echo "submit via:"
    echo "${sub}"
    exit 0
fi
    
# submit job
jobid=($(${sub}))
jobid=${jobid[3]}
taskid=1

# rename the err/output files as we now know the jobid
error=`echo ${error} | sed "s/%A/${jobid}/"`
output=`echo ${output} | sed "s/%A/${jobid}/"`

# record submission
track_task.py queue --jobid=${jobid} --taskid=${taskid} --task='apply_cal' --submission_time=`date +%s` --batch_file=${script} \
                     --obs_id=${obsnum} --stderr=${error} --stdout=${output}

echo "Submitted ${script} as ${jobid}. Follow progress here:"
echo $output
echo $error

