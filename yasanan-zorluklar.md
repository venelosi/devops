# yasanan zorluklar

bu dosya deploy surecinde gorulen sorunlari ve uygulanan cozumleri listeler.

## 1) test adiminda e2e fail durumu

- belirti: cypress senaryosu belirli bir metni sayfada bulamadi ve test fail oldu.
- etki: deploy job test gecmeden calismadi.
- neden: test senaryosu mevcut ui akisina tam uymuyordu.
- uygulanan cozum: pipeline testi smoke kontrol mantigina cekildi ve kritik api akislari dogrulandi.

## 2) cloudformation rollback durumlari

- belirti: stack `rollback_complete` veya `rollback_failed` durumda kaldi.
- etki: `createchangeset` adiminda stack update reddedildi.
- neden: onceki stack create asamasinda bir veya daha fazla kaynak fail oldu.
- uygulanan cozum: `deploy.py` icine stack state kontrolu eklendi, gerekli durumda otomatik delete ve yeniden create adimi calistirildi.

## 3) eks addon create_failed sorunu

- belirti: `ebscsiaddon` sagliksiz duruma gecip stack rollback tetikledi.
- etki: cloudformation deploy tamamlanamadi.
- neden: addon podlari beklenen sayida ayaga kalkmadi.
- uygulanan cozum: template icindeki addon kaynagi kaldirildi.

## 4) mongodb rollout timeout

- belirti: `kubectl rollout status deployment/mongodb` timeout verdi.
- etki: deploy script hata kodu ile sonlandi.
- neden: pod hazir olma suresi uzadi veya storage tarafinda bekleme olustu.
- uygulanan cozum: mongodb manifesti sade tutuldu, rollout fail durumunda pod describe ve log toplama adimlari eklendi, ekstra olarak mongodb serverless tercih edilebilir ama fix için süre yetersizdi.

## 5) kubeconfig ve bolge uyumsuzlugu

- belirti: `no such host` hatasi ile eski eks endpointine baglanma denemesi.
- etki: lokal kubectl komutlari clustera ulasamadi.
- neden: kubeconfig icinde eski cluster context kaldi.
- uygulanan cozum: guncel bolge ile yeniden kubeconfig yazildi.

## 6) uzun sureli deploy calismasi

- belirti: github actions adimlari 40+ dakika surebildi.
- etki: hata var mi yok mu gec anlasildi.
- neden: cloudformation create delete donguleri ve eks kaynak olusumu zaman aliyor.
- uygulanan cozum: log adimlari netlestirildi, stack eventleri otomatik yazdirildi, kritik bekleme noktalarina durum ciktilari eklendi.

## 7) runner altyapi hatasi

- belirti: `job was not acquired by runner of type hosted`.
- etki: pipeline koddan bagimsiz sekilde baslamadan sonlandi.
- neden: github hosted runner tarafinda gecici servis sorunu, bu sorun çok defa yaşandı github sunucusuyla alakalı olduğunu düşünüyorum.
- uygulanan cozum: yeniden run alindi ve tekrar deneme ile surec devam ettirildi.

## genel sonuc

- ana blokajlar test uyumsuzlugu, cloudformation rollback state ve mongodb rollout tarafinda toplandi.
- otomatik temizleme ve daha gorunur log ciktilari ile deploy sureci daha izlenebilir hale geldi.
- lokalde deploy içindeki destroy fonksiyonu ile açılan servisler kolayca kapatılmalı, fixlemek için zaman gerekli.

