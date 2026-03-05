## nasil kullanilir

1. onkosullar:
   - github secrets icinde `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_ACCOUNT_ID` olmasi gerekir.
   - lokalde `docker`, `aws cli`, `kubectl`, `python 3` kurulu olmalidir.
2. lokal calistirma:
   - repo kokunde `docker compose up -d` calistir.
3. ci cd deploy:
   - repoya push atildiginda `.github/workflows/ci-cd.yaml` tetiklenir
   - test adimi gecerse deploy adimi `python deploy.py --tag <commit_sha>` ile devam eder
   - herhangibir hata durumunda burada loglar incelenebilir.
4. deploy sonrasi url alma:
   - `aws eks update-kubeconfig --name mern-devops-cluster --region eu-west-1`
   - `kubectl get svc client -n mern-devops -o jsonpath="{.status.loadBalancer.ingress[0].hostname}"`
5. manuel komutlar:
   - temizleme: `python deploy.py --destroy`(geliştirme aşamasında)

# proje ozeti

bu repo mern uygulamasi, python etl gorevi ve aws uzerindeki eks altyapisini tek yerde tutar.
hedef, kod push sonrasi test ve dagitim adimlarini otomatik calistirmaktir.

## kapsam

- `mern-project/client`: react tabanli arayuz
- `mern-project/server`: node express api katmani
- `python-project/ETL.py`: saatlik cron ile calisan etl gorevi
- `infrastructure/cloudformation.yaml`: aws kaynaklarini olusturan altyapi tanimi
- `infrastructure/kubernetes/*.yaml`: kubernetes namespace, deployment, service ve cronjob tanimlari

## gereksinimler

- aws hesabi ve yeterli izinlere sahip bir iam kullanicisi
- github repository secrets icinde `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` ve `AWS_ACCOUNT_ID`
- lokal deneme icin docker, aws cli, kubectl ve python 3
- varsayilan bolge olarak `eu-west-1`

## dagitim sureci detayli

1. repository icine push yapildiginda `.github/workflows/ci-cd.yaml` tetiklenir.
2. ilk job test adimidir.
3. test adiminda `docker compose up -d` ile lokal benzeri servisler kaldirilir.
4. backend health endpoint kontrol edilir.
5. frontend acilmasi beklenir.
6. basit bir smoke kontrol yapilir:
   - api uzerinden kayit ekleme
   - eklenen kaydi backendden geri okuma
   - frontend proxy rotasi uzerinden ayni veriyi gorme
7. test basariliysa deploy job calisir.
8. deploy job icinde aws kimlik bilgileri yuklenir.
9. `python deploy.py --tag <commit_sha>` komutu ile ana dagitim akisi baslar.
10. script once cloudformation stack durumunu okur.
11. stack `rollback_complete` veya `rollback_failed` gibi guncellenemeyen durumda ise stack silme adimi calisir(kişisel kontrol gerekli).
12. stack temizlendikten sonra `aws cloudformation deploy` ile altyapi create update edilir.
13. cloudformation output degerleri alinip sonraki adimlarda kullanilir.
14. uc container image build edilir:
   - client image
   - server image
   - etl image
15. image dosyalari ecr repositorylerine push edilir.
16. `aws eks update-kubeconfig` ile kubectl context eks clustera baglanir.
17. kubernetes manifestleri sirayla apply edilir.
19. rollout basariliysa deploy adimi tamamlanir(servislerin ayağa kalkması için biraz beklemek gerekiyor, bu sadece fonksiyon başarılı oldu demek).
20. en sonda frontend service bilgisi loga basilir.

## mimari detayli

### altyapi katmani

- vpc, public subnet, private subnet ve route kaynaklari cloudformation ile olusur.
- internet gateway ve nat gateway ile ag cikisi saglanir.
- eks control plane cluster seviyesi yonetimi saglar.
- nodegroup uzerinde uygulama podlari calisir.
- ecr tarafinda her servis icin ayri image deposu bulunur.

### uygulama katmani

- client servisi dis dunyaya `loadbalancer` tipi service ile acilir.
- server servisi cluster ici `clusterip` ile erisilir.
- mongodb servisi server tarafindan dahili agdan kullanilir.
- etl gorevi `cronjob` olarak planli sekilde calisir.

### trafik akisi

1. kullanici istekleri once `client` loadbalancer adresine gelir.
2. react uygulamasi api isteklerini `server` servisine proxy eder.
3. server uygulamasi veriyi mongodb deploymentina yazar ve okur.
4. etl gorevi belirlenen zamanlarda harici kaynaktan veri cekip isler.

### veri kaliciligi notu

- mevcut konfigde mongodb icin gecici hacim kullaniliyor(mongodb serverless çözümü otomasyona eklemek için ek süre gerekiyor).
- pod yeniden olursa veri kaybi olusabilir.
- kalici ortam icin uygun storage class ve pvc duzeni gerekir.

## dagitim sonrasi kontrol adimlari

1. cluster baglantisi:
   `aws eks update-kubeconfig --name mern-devops-cluster --region eu-west-1`
2. pod kontrolu:
   `kubectl get pods -n mern-devops`
3. service kontrolu:
   `kubectl get svc -n mern-devops`
4. frontend adresi alma:
   `kubectl get svc client -n mern-devops -o jsonpath="{.status.loadBalancer.ingress[0].hostname}"`
5. rollout durumu kontrolu:
   `kubectl rollout status deployment/mongodb -n mern-devops --timeout=120s`

## pipeline loglarinda beklenen kritik noktalar

- cloudformation adiminda `successfully created/updated stack`
- docker push adimlarinda image digest ciktilari
- kubernetes apply adiminda `created` veya `configured` mesaji
- rollout adimlarinda timeout olmamasi
