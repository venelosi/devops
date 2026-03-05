# MERN DevOps

## Gereksinimler

- Docker
- AWS CLI (`aws configure` yapilmis olmali)
- kubectl
- Python 3
- GitHub hesabi

## Kurulum (Tek Seferlik)

1. GitHub'da yeni repo olusturun
2. Settings > Secrets and variables > Actions'a gidin
3. Su 3 secret'i ekleyin:

| Secret | Deger |
|--------|-------|
| AWS_ACCESS_KEY_ID | AWS Access Key |
| AWS_SECRET_ACCESS_KEY | AWS Secret Key |
| AWS_ACCOUNT_ID | 12 haneli AWS hesap numarasi |

4. Kodu push edin:
```bash
aws configure
git init && git add . && git commit -m "init"
git remote add origin https://github.com/KULLANICI/REPO.git
git push -u origin main
```

Ilk push'ta CI/CD otomatik olarak:
1. Test calistirir (healthcheck + Cypress)
2. CloudFormation ile VPC + EKS + ECR olusturur
3. Docker image'lari build + push eder
4. MongoDB + Server + Client + ETL deploy eder
5. CloudWatch alarm + autoscaling kurar

## Sonraki Push'lar

Her `git push` otomatik olarak:
- CloudFormation: degisiklik yoksa atlar
- Docker: yeni image build eder (git SHA tag'i ile)
- K8s: sadece image degisen pod'lari gunceller, gerisine dokunmaz
- Yeni manifest eklediyseniz otomatik uygular

## Lokal Deploy (Opsiyonel)

Lokal makineden de deploy edebilirsiniz:
```bash
python deploy.py
python deploy.py --tag v1.0.0
```

## Silme

```bash
python deploy.py --destroy
```

## Lokal Test

```bash
docker compose up -d
```
Frontend: http://localhost:3000 | Backend: http://localhost:5050
(Lokal test icin MongoDB container kullanilir, Atlas gerekmez)
