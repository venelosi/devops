#!/usr/bin/env python3
#linux ortam için bu
import subprocess, sys, json, shutil
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
CF_TEMPLATE = ROOT / "infrastructure" / "cloudformation.yaml"
K8S_DIR = ROOT / "infrastructure" / "kubernetes"
DOCKER_DIR = ROOT / "infrastructure" / "docker"
STACK = "mern-devops"
REGION = "eu-west-1"


def get_arg(name, default=None):
    for i, a in enumerate(sys.argv):
        if a == f"--{name}" and i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def log(msg):
    print(f"\n[DEPLOY] {msg}")


def run(cmd, capture=False, check=True):
    log(f"$ {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=capture, text=True)
    if check and r.returncode != 0:
        if r.stderr: print(r.stderr)
        sys.exit(1)
    return r


def get_account():
    r = run("aws sts get-caller-identity", capture=True, check=False)
    if r.returncode != 0:
        log("AWS CLI yapilandirilmamis. Once 'aws configure' calistirin.")
        sys.exit(1)
    return json.loads(r.stdout)["Account"]


def deploy():
    for tool in ["docker", "aws", "kubectl"]:
        if not shutil.which(tool):
            log(f"'{tool}' bulunamadi. Lutfen yukleyin.")
            sys.exit(1)

    tag = get_arg("tag", "latest")
    account = get_account()
    registry = f"{account}.dkr.ecr.{REGION}.amazonaws.com"

    log("1/6 - CloudFormation stack olusturuluyor (degisiklik yoksa atlar)...")
    run(f'aws cloudformation deploy --template-file "{CF_TEMPLATE}" --stack-name {STACK} '
        f'--capabilities CAPABILITY_NAMED_IAM --region {REGION} --no-fail-on-empty-changeset')

    r = run(f'aws cloudformation describe-stacks --stack-name {STACK} --region {REGION} '
            f'--query "Stacks[0].Outputs"', capture=True)
    outputs = {o["OutputKey"]: o["OutputValue"] for o in json.loads(r.stdout)}
    cluster = outputs["ClusterName"]
    ecr = {c: outputs[f"ECR{c.capitalize()}Url"] for c in ["client", "server", "etl"]}


    log(f"2/6 - Docker image'lari build ediliyor (tag: {tag})...")
    run(f"aws ecr get-login-password --region {REGION} | docker login --username AWS --password-stdin {registry}")
    for comp, repo in ecr.items():
        run(f"docker build -f {DOCKER_DIR}/Dockerfile.{comp} -t {repo}:{tag} .")
        run(f"docker push {repo}:{tag}")

    log("3/6 - kubectl yapilandiriliyor...")
    run(f"aws eks update-kubeconfig --name {cluster} --region {REGION}")

    log("4/6 - K8s manifest'leri uygulaniyor (degisiklik yoksa dokunmaz)...")
    run("kubectl apply -f " + str(K8S_DIR / "namespace.yaml"))

    tmp = ROOT / ".k8s-tmp"
    tmp.mkdir(exist_ok=True)
    for f in K8S_DIR.glob("*.yaml"):
        if f.name == "namespace.yaml":
            continue
        content = f.read_text(encoding="utf-8")
        for comp, repo in ecr.items():
            content = content.replace(f"${{ECR_REPO}}/{comp}", repo)
        content = content.replace(":latest", f":{tag}")
        (tmp / f.name).write_text(content, encoding="utf-8")

    for f in sorted(tmp.glob("*.yaml")):
        run(f"kubectl apply -f {f}")

    run("kubectl rollout status deployment/mongodb -n mern-devops --timeout=120s")
    run("kubectl rollout status deployment/server -n mern-devops --timeout=120s")
    run("kubectl rollout status deployment/client -n mern-devops --timeout=120s")
    shutil.rmtree(tmp, ignore_errors=True)

    log("5/6 - Autoscaling ayarlaniyor (CPU > 80% -> yeni node ekle)...")
    setup_autoscaling(cluster)

    log("6/6 - Kontrol ediliyor...")
    run("kubectl get pods -n mern-devops")
    run("kubectl get svc client -n mern-devops")
    log("Deploy tamamlandi!")
    log("Frontend URL icin: kubectl get svc client -n mern-devops")


def setup_autoscaling(cluster):
    ng = run(f'aws eks list-nodegroups --cluster-name {cluster} --region {REGION} '
             f'--query "nodegroups[0]" --output text', capture=True)
    asg = run(f'aws eks describe-nodegroup --cluster-name {cluster} --nodegroup-name {ng.stdout.strip()} '
              f'--region {REGION} --query "nodegroup.resources.autoScalingGroups[0].name" --output text',
              capture=True)
    asg_name = asg.stdout.strip()
    r = run(f'aws autoscaling put-scaling-policy --auto-scaling-group-name {asg_name} '
            f'--policy-name cpu-scale-up --policy-type SimpleScaling '
            f'--adjustment-type ChangeInCapacity --scaling-adjustment 1 --cooldown 300',
            capture=True)
    policy_arn = json.loads(r.stdout)["PolicyARN"]
    run(f'aws cloudwatch put-metric-alarm --alarm-name {cluster}-cpu-high '
        f'--metric-name CPUUtilization --namespace AWS/EC2 --statistic Average '
        f'--period 300 --threshold 80 --comparison-operator GreaterThanThreshold '
        f'--dimensions Name=AutoScalingGroupName,Value={asg_name} '
        f'--evaluation-periods 2 --alarm-actions {policy_arn}')


def destroy():
    if input("Silmek icin 'yes' yazin: ").lower() != "yes":
        return
    run(f"aws cloudwatch delete-alarms --alarm-names {STACK}-cluster-cpu-high --region {REGION}", check=False)
    run("kubectl delete namespace mern-devops --ignore-not-found", check=False)
    log("NLB'nin silinmesi bekleniyor (90sn)...")
    import time; time.sleep(90)
    for repo in [f"{STACK}/client", f"{STACK}/server", f"{STACK}/etl"]:
        run(f"aws ecr delete-repository --repository-name {repo} --region {REGION} --force", check=False)
    run(f"aws cloudformation delete-stack --stack-name {STACK} --region {REGION}")
    run(f"aws cloudformation wait stack-delete-complete --stack-name {STACK} --region {REGION}")
    log("Tum kaynaklar silindi!")


if __name__ == "__main__":
    if "--destroy" in sys.argv:
        destroy()
    else:
        deploy()
