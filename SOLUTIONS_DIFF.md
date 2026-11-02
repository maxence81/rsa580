# Diff des solutions des paliers précédents (500 → 530)

**Date** : 2026-11-02
**Source** : zips « Download Solution » déposés dans `C:\Users\maxen\enigma_rsa\*.zip`,
extraits hors dépôt dans `C:\Users\maxen\sol_enum\`.

Ce document répond à une seule question : **qu'est-ce qui a fait avancer la
frontière à chaque palier, et qu'est-ce que ça change pour le 580 ?**

---

## 0. Ce que contient le lot

Six solutions distinctes, plus notre propre 560 (`964dd74e…`). Identification par
la taille de cible et les paramètres, pas par la date (certains zips ont des
horodatages remis à zéro).

| zip | palier | cible | cribleur | relations | temps mesuré |
|---|---|---|---|---|---|
| `fd50a0d5` | ≤ 440 | — | **aucun GNFS** : trial division + Pollard-rho + yafu SIQS | — | — |
| `0cc00b8d` | **460** | c140 | `gpu_loop` (CUDA maison, 43 Ko) | 60 M | ~3,5 h (doc) |
| `ede98578` | **480** | c145 | `gpu_loop` (binaire seul) | 96,35 M | — |
| `b1bcaf7c` | **500** | c151 | `gpu_loop` (186 Ko) | 72 M | — |
| `e6c212c4` | **512** | c154/c155 | `gpu_loop` (222 Ko) | 61 M brutes / 40,7 M uniques | 12 413 s (c154) |
| `badf0faf` | **530** | c160 | **`cuda-sieve`** (public) | 160 M (sonde) | **14 368,7 s** |

**Le 560 manque.** Le lot s'arrête au 530. C'est le palier qui nous intéresse le
plus (c160 → c175 est le saut qu'on doit franchir), et c'est justement celui
qu'on n'a pas.

---

## 1. La chronologie technique

### 1.1 Phase « méthodes bon marché » (≤ 440)

`fd50a0d5` ne fait aucun GNFS : division par les petits premiers, Pollard-rho
borné, puis **yafu SIQS**. Six fichiers, 47 Ko. C'est le palier où le GNFS n'est
pas encore nécessaire.

### 1.2 Phase `gpu_loop` : le cribleur maison (460 → 512)

Toute la progression 460→512 se fait avec **`gpu_loop`**, un cribleur lattice GPU
écrit de zéro par la même équipe (« Xin / Xdev »). Sa taille de source raconte la
progression :

```
c140  43 Ko     c145  binaire seul     c151  186 Ko     c154/155  222 Ko
```

À c140 il fait **17 ms/lattice** et sort ~75 M relations en 2–3 h. À c154/155 il
descend à **5,0 ms/lattice** (`MS_PER_LAT = 5.0`, mesuré plat sur toute la plage
de q) — soit **3,4× plus rapide par lattice en quatre paliers**.

Le point non trivial de cette phase n'est pas le crible, c'est **la gestion du
disque**. Le validateur ne donne que 1 Gio de `/tmp` inscriptible, alors que les
intermédiaires pèsent 10–20 Go. Leur réponse : un broker `memhold.py` /
`msv_launcher` qui garde tout en RAM anonyme via `memfd_create` et expose les
fichiers à msieve/CADO par des symlinks `/proc/<pid>/fd/N`. Pic `/tmp` mesuré :
**114 Mo** (bon polynôme) à **204 Mo** (polynôme faible).

### 1.3 Le saut 512 → 530 : abandon du cribleur maison

C'est le fait marquant du diff. **À partir du 530, `gpu_loop` disparaît** et le
pipeline passe à **`cuda-sieve`**, un projet **public** :

```
cuda-sieve: https://github.com/kyleaskine/cuda-sieve commit db85a39 (2026-09-25), CC0-1.0
```

Le driver `factor_c160.sh` l'appelle ainsi :

```
cuda-sieve bench --pipeline --cofactor --fill-concurrent
  lpb 31/31  mfb 61/62  lim 100M/150M  A 28  J 16384  logI 15
  qmin 2.2M  FIRST_PROBE 160M  chunks de 8M (4M en fin de plage)
  24,1 ms/q   →   run complet 14 368,7 s
```

Autrement dit : **l'équipe qui gagnait avec son propre cribleur l'a jeté pour un
cribleur public dès qu'elle a eu besoin de plus de capacité.** C'est l'information
la plus utile du lot.

### 1.4 Ce que le 530 a coûté

`polyselect_best.sh:200` : *« End-to-end on key 20260916: 14 368,7 s »* — sur une
limite de 14 400 s. **31 secondes de marge.** Le 530 a consommé tout le budget.

C'est cohérent avec ce que la page des challenges montre pour le 560 (~14 255 s) :
chaque palier récent se gagne à 99,8 % du temps autorisé. La chaîne n'a plus de
slack depuis le 512.

---

## 2. La découverte qui rouvre le dossier

Le dossier RSA-580 a été clos le 2026-11-02 sur une prémisse explicite :

> « il faudrait **un cribleur GPU capable de 3LP** […] c'est un autre binaire, pas
> un patch. Rien de tel n'est disponible ici. »

**Cette prémisse est fausse.** `cuda-sieve` :

- est **domaine public (CC0-1.0)** — pas de licence à négocier, pas de reverse
  engineering ;
- gère **jusqu'à trois grands premiers par côté** (`lpb ≤ 64` est une limite
  vérifiée), avec **choix automatique de la méthode par côté** : Pollard-Brent
  rho pour un côté 2LP, **ECM pour un côté 3LP** ;
- fait la **cofactorisation sur GPU**, avec largeur arithmétique 3 ou 4 membres
  choisie d'après `mfb`/`lpb` ;
- tourne sur **Blackwell sm_120**, c'est-à-dire exactement notre GPU.

Et surtout : **les binaires sont déjà dans le zip du 530**, compilés pour notre
architecture.

| binaire | taille | arch | dépendances |
|---|---|---|---|
| `bench` | 11,5 Mo | `sm_120` (+ `sm_30`, `sm_70`) | `libcuda.so.1`, `libm.so.6` |
| `cofac_cpu` | 1,5 Mo | x86-64, **0 instruction AVX-512** | CADO `facul` lié statiquement |
| `fbgen_gpu` | 2,8 Mo | `sm_120` | `libcuda.so.1` |

Pas de dépendance à `libcudart` : le runtime CUDA est lié statiquement. Les trois
fichiers se copient dans notre image et doivent tourner tels quels.

**Ce que ça annule** : le verdict « il faut écrire un cribleur 3LP, projet de
plusieurs semaines ». Le cribleur existe, il a gagné le 530, et il est dans nos
mains depuis ce matin.

**Ce que ça ne dit pas** : si la 3LP suffit à faire tenir c175 dans 14 400 s. Ça,
seule une mesure le dira — et elle coûte quelques minutes, pas quelques semaines.

---

## 3. L'arithmétique du saut c160 → c175

Les deux seuls points de mesure exploitables :

| | c160 (530 bits) | c175 (580 bits) |
|---|---|---|
| relations nécessaires | **160 M** (sonde mesurée) | **441 M** (notre mesure, 2LP) |
| coût par q | 24,1 ms/q | inconnu |
| temps total | 14 368,7 s | inconnu |

Le besoin en relations est multiplié par **2,76×** pour 50 bits de plus. Et le
530 disposait déjà de 31 s de marge. **En 2LP, le 580 est hors de portée par un
facteur ~2,7** — ce que nos mesures disaient déjà.

La 3LP est le seul mécanisme qui casse ce rapport : elle divise le besoin en
relations. Notre propre essai 3LP à c175 visait **199 M** relations contre 441 M
en 2LP, soit **2,2× moins**. Si le débit tient, `199 M / 22 000 rel/s ≈ 9 000 s`
de crible — largement dans le budget.

Tout dépend donc de deux nombres inconnus à c175 en 3LP : **relations par q** et
**ms par q**. Les deux se lisent sur une bande de quelques minutes.

---

## 4. Le test qui tranche, et son coût

Faire tourner `bench` sur **notre polynôme c175** en mode 3LP, sur une bande de q
courte, et lire :

- `ms/q` (coût) ;
- `rel/q` et le taux d'acceptation de la cofactorisation ;
- le taux de rejet ECM (`--cof-budget`, la sortie signale déjà « a healthy 3LP
  band runs ~20% » de cofacteurs non résolus).

Projection ensuite : `199 M / (rel par q × 1000 / ms par q)` secondes.

**Coût** : une poignée de minutes de GPU, moins de 1 $. À comparer aux 9–10 $
déjà dépensés pour mesurer une chaîne qu'on savait condamnée.

Trois issues :

| résultat | conséquence |
|---|---|
| ≥ 22 000 rel/s en 3LP | 199 M tient en ~9 000 s → **le 580 redevient jouable** |
| 12 000–22 000 rel/s | 9 000–16 600 s de crible → marginal, il faut rogner ailleurs |
| < 12 000 rel/s | la 3LP ne sauve pas → dossier réellement clos, cette fois avec le bon outil mesuré |

---

## 5. Réserves honnêtes

1. **Le 560 manque.** On ne sait pas quelle chaîne l'a gagné. S'il utilise déjà
   `cuda-sieve` en 3LP, alors le 580 est peut-être à portée d'un simple
   changement de paramètres — ou peut-être que l'équipe du 560 a déjà buté sur ce
   qu'on va buter.
2. **Intégration non triviale.** Le pipeline du 530 suppose `memhold.py`,
   `cado_incdup.sh`, `cado_filter160.sh`, `ds_cado.sh` et un CADO instrumenté
   (`freerel`, `dup1/dup2`, `purge`, `merge`, `replay`, `characters`, `sqrt`).
   Ce sont des scripts, pas des binaires : ils sont dans le zip et lisibles.
3. **`bench` est un binaire, pas une source.** On peut le lancer, pas le corriger.
   Le dépôt public est là si un patch devient nécessaire.
4. **La mesure de débit de `gpu_loop` ne se transpose pas à `cuda-sieve`.** Ce
   sont deux cribleurs différents ; seul `cuda-sieve` compte désormais.

---

## 6. Ce que ce diff change dans le dossier

| affirmation du dossier | statut |
|---|---|
| « aucun cribleur GPU 3LP disponible » | **faux** — `cuda-sieve`, CC0, binaires en main |
| « il faudrait écrire un cribleur, plusieurs semaines » | **faux** — il existe et a gagné le 530 |
| « le 580 est hors de portée de cette chaîne » | **toujours vrai pour GLAS 2LP**, seule chaîne mesurée |
| « le 580 est hors de portée, point » | **non démontré** — la chaîne qui pourrait le faire n'a pas été mesurée |
| « le 560 a été gagné à 14 255 s » | vrai, et cohérent : le 530 aussi était à 31 s de la limite |

Le dossier n'est pas rouvert par un espoir, il est rouvert par **un binaire qui
existe, qui tourne sur notre GPU, et qui fait exactement la chose dont on avait
conclu qu'elle était indisponible**.

---

## 7. Reproduire cette analyse

Les six zips sont à la racine du dépôt (`*.zip`, exclus de git). Extraction :

```bash
for f in 0cc00b8d-*.zip b1bcaf7c-*.zip badf0faf-*.zip e6c212c4-*.zip \
         ede98578-*.zip fd50a0d5-*.zip; do
  d="/c/Users/maxen/sol_enum/$(echo "$f" | cut -c1-8)"
  mkdir -p "$d" && unzip -qo "$f" -d "$d"
done
```

Les binaires `cuda-sieve` utilisables sont dans
`sol_enum/badf0faf/cuda-sieve/` (`bench`, `cofac_cpu`, `fbgen_gpu`), accompagnés
de leur provenance complète dans `badf0faf/licenses/cuda-sieve-PROVENANCE.txt`.

Pour reconstruire plutôt que réutiliser :

```bash
git clone https://github.com/kyleaskine/cuda-sieve && cd cuda-sieve
git checkout db85a39
make bench fbgen fbgen_gpu normscan GPU_ARCH=120 CF_LMAX=3 BN_LIMBS=12 \
     HOST_TUNE=-march=x86-64-v3 CUDART_LINK=static
```

dans `nvidia/cuda:13.0.1-devel-ubuntu24.04`. C'est la ligne exacte utilisée par
la solution du 530, recopiée de son fichier de provenance.
