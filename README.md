## Parallel Cluster Prod Notes and Config

### AWS Notes

#### Storage Layer

FSX and EFS are the two primary shared file systems available. FSX has the benefit of being able to be cloned into S3 as a backup. 

FSX is the high performance scratch space,

EFS is used for storing home directories.

S3FS installed on the master node only to allow copying of data from s3 into the work directories.

#### Compute Instance Type

We must use intel processors, BWA has an issue running on any AMD processors (noted by an "a" in the instance name)

Since we use spot instances to reduce cost as aws batch we need to select an instance type that has low interruption.

[This table](https://aws.amazon.com/ec2/spot/instance-advisor/) links to the cost savings and interruption percentage of EC2 instances. Instance size needs to be as large as the most compute intensive tool requires as we aren't using aws batch to define requirements. In this case STAR requires at the very minimum 32GB of ram. 

Looking at the document, the new group of instances m5dn.12xlarge has a high core count (48 threads) and 192gb memory, has 85% cost savings at $3.264/hr * (1 - .85) = **$0.50/hr**

The other option is c5n.18xlarge which has 72 threads 192gb memory, has a cost savings at $3.06/hr * (1 - .82) = **$0.55/hr**

|  INSTANCE TYPE    |  COST/HR  | SAVINGS  | NEW COST/HR
|---|---|---|---
| m5dn.12xlarge |  $3.264   | 85%  | $0.50
| c5n.18xlarge  |  $3.06    | 82%  | $0.55

#### Master Instance Type

This instance is on-demand with no interruption, however it will be running cromwell which can take up substantial memory when copying files. It is currently using an m4.4xlarge which has 64GB of memory, more than enough to manage cromwell and job submission.

#### OS Type

We are using amazon linux 2 as it allows the most options if we want to change schedulers and is most well documented and supported by AWS.

#### Scheduler

The slurm scheduler is used as it is the simplest to manage and setup, the commands are well defined and there are many documents that explain how to use it. [Example](https://www.brightcomputing.com/blog/bid/174099/slurm-101-basic-slurm-usage-for-linux-clusters)

#### Queue Size

We keep 1 compute node constantly alive in order to kick off workloads without having to wait for all the other nodes to startup.

#### Maintenance Tasks

- Monthly dump of docker cache
- Monthly sync of reference files to disk

### Deploying Parallel-Cluster

Before running this make sure your aws cli is setup with ```aws configure```.

First clone the repo and setup the conda env included in the repo and install the latest parallel cluster.

```bash
git clone https://gitlab.com/iidsgt/parallel-cluster.git
cd parallel-cluster
conda env create -f environment.yml
```

Next, run the the script to add arguments to the parallel cluster config.

```
python config_builder.py --cromwell_user={cromwell db username} --cromwell_password={cromwell db password} --s3_key={s3_key_id} --s3_secret={s3_key_secret}
```

This will write a file called ```PC-Prod-Built.cfg``` that can be run with the pcluster command.

To deploy using this file run

```bash
pcluster create -c ./PC-Prod-Built.cfg pcprod --norollback
```

### Useful PCluster Commands

#### Update a cluster

```bash
pcluster update -c {config file} {cluster name}
pcluster update -c ./aws.conf gridcluster
```

#### Delete a cluster

```bash
pcluster delete -c {config file} {cluster name}
pcluster delete -c ./aws.conf gridcluster
```

#### Get cluster info

Returns info relevant to a cluster in the format below.


```bash
pcluster status -c {config file} {cluster name}
pcluster status -c ./aws.conf gridcluster
```
Returns:
```
Status: CREATE_COMPLETE
MasterServer: RUNNING
ClusterUser: ec2-user
MasterPrivateIP: 10.0.0.66
```

### Tests

To run tests on the post install python script simply clone the repo and build and run the compute and master dockerfiles.

***Tests will fail! Specifically the systemd start commands in docker. It is very difficult to get running without privileged containers.***

```
git clone https://gitlab.com/iidsgt/parallel-cluster.git
docker build -t master -f ./tests/post-script/Master.Dockerfile . && docker run master
```

### Useful SLURM Commands

#### Submit an interactive job

```bash
srun -p compute {command here}
srun -p compute hostname
```

#### Submit an asynchronous job

This will submit a job to the queue and write the stdout and stderr to a file of the name slurm-{jobid}.out

```bash
sbatch -p compute --wrap="{command here}"
sbatch -p compute --wrap="hostname"
```

#### See the current queue

```bash
squeue
```

#### Get job information

```bash
scontrol show job {jobid}
scontrol show job 4617
```

#### Cancel a job

```bash
scancel {jobid}
scancel 4617
```

### Extras

#### LDAP

GLAuth is setup on the Master node to serve as the simple directory server. Users and groups are added by adding to the glauth.cfg file in ```/opt/glauth/```.

User blocks are created as shown below. 

```conf
[[users]]
  name = "user_name"
  givenname="user"
  sn = "name"
  mail = "user_name@mail.com"
  unixid = 8002
  primarygroup = 8501
  loginShell = "/bin/bash"
  homeDir = "/path/to/home/dir"
  sshkeys = ["ssh-rsa foo bar"]
```

There are also password fields that can be added if you would like to enable password based authentication, however in our setup it is best to only use public/private key authentication.

Groups are created as show below.

```conf
[[groups]]
    name = "docker"
    unixid = 980
    includegroups = [8501]

```

The ```includegroups``` section indicates which group this group should be a secondary group of. So if you had another at 8501 this would now be a group all members of 8501 would be a part of.


#### Jupyter

**Requires Anaconda to be installed**

Before running a notebook make sure to set a password otherwise it will have issues connecting.

```bash
jupyter notebook password
```

You can use the following bash function to launch an interactive notebook. You will need to have the full version of anaconda installed in your home directory. 

```bash
nb() {
    RED='\033[0;31m'
    CYAN='\033[0;36m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
    while
        port=$(shuf -n 1 -i 49152-65535)
        netstat -atun | grep -q "$port"
    do
        continue
    done
    jdc=$(sbatch -p compute --wrap="jupyter notebook --no-browser --port=$port")
    job_id=$(echo "$jdc" | sed -r  's/^[^0-9]*([0-9]+).*/\1/')
    node=$(scontrol show job "$job_id" | sed -n 's/   NodeList=//p')
    while [ "$node" == "(null)" ]
    do
        node=$(scontrol show job "$job_id" | sed -n 's/   NodeList=//p')
    done
    echo -e "${RED}Paste the following to connect to the notebook"
    echo -e "${YELLOW}ssh -t -t $USER@cluster.iidsgt.org -L $port:localhost:$port ssh $node -L $port:localhost:$port"
    echo -e "\n${CYAN}Then visit: http://localhost:$port ${NC}"
}
```

### Notes

EFA may work on m5dn but it isn't in the notes