# Journal complet des tentatives — RSA-580 / Enigma Subnet 63

**Date** : 2026-11-01 → 2026-11-02
**Cible** : semi-premier équilibré 580 bits (~175 chiffres, c175)
**Limite** : 14 400 s (4 h) — confirmée par l'API publique des challenges
**Machine** : RTX PRO 6000 96 Go VRAM, 24 vCPU, 85 Go RAM, `--network none`, `--read-only`, tmpfs 10 Go
**Statut final** : non résolu, **hors de portée par mesure**. Tous les leviers —
logiciels, mathématiques et matériels — sont fermés ou mesurés. Le run du §14
donne **269,9 M relations à 12 160 s** quand le budget n'en autorise que ~304 M
pour un besoin de 441 M : déficit **1,45×** en relations, total projeté
**23 244–23 942 s** contre 14 400 s. Le §13.8 liste les corrections apportées au
chiffrage antérieur après revue contradictoire ; le §14 les remplace par une
mesure.

---

## Sommaire

1. [Phase 1 — Run initial (31/10/2026)](#phase-1)
2. [Phase 2 — Diagnostic structurel : les caps GLAS](#phase-2)
3. [Phase 3 — Tests 3LP et caps (01/11 matin)](#phase-3)
4. [Phase 4 — Balayage des régimes et loi de coût (01/11 après-midi)](#phase-4)
5. [Phase 5 — Polyselect et polynôme P](#phase-5)
6. [Phase 6 — Correction majeure : le coude de débit](#phase-6)
7. [Phase 7 — Reprise Modal, panne proxy, mesure décisive (01/11 soir)](#phase-7)
8. [Phase 8 — Essai 3LP final](#phase-8)
9. [Bilan global des leviers testés](#bilan)
10. [Verdict et conditions de reprise](#verdict)
11. [Revue de la littérature (02/11) — tri des sources et piste révélée](#litterature)
12. [McGuire-Robinson — évalué, écarté](#mcguire)
13. [Phase 9 — Le dernier levier (nombre de GPU) et clôture définitive](#phase-9)
14. [Phase 10 — Le run qui tranche : mesure directe du profil 560 sur c175](#phase-10)
15. [Phase 11 — Les solutions des paliers précédents rouvrent le dossier](#phase-11)

---

<a id="phase-1"></a>
## 1. Phase 1 — Run initial (31/10/2026)

**Configuration** :
- `LPB 32/34`, `MFB 64/68`, `RLIM 250M`, `ALIM 600M`
- Co-crible CPU LAS activé
- `FIRST_PROBE 473M`
- Profil Modal : `lol810-maxou`

**Résultats** :
- Pic initial : ~49 000 rel/s
- Débit fin de crible : ~32 500 rel/s
- Relations atteintes avant arrêt : 517 360 467
- `/tmp` : ~6,9 Go (sous la limite 10 Go)
- Première sonde (476 890 759 raw) : `SHORT`, unique=345 637 771, ncols=29 566 131
- Deuxième sonde (488 764 412 raw) : `SHORT`, unique=353 111 364, ncols=30 284 709
- Crossover annoncé : 528 764 412 → arrêt à 517 360 467 (manquait 12 min)

**Découverte ultérieure** : le crossover annoncé était un **plafond de clamp**, pas une estimation. `stop_cost.py` clampe son point prédit dans `[PROBE_AT + PROBE_STEP/2, PROBE_AT + 4×PROBE_STEP]`. Le vrai crossover linéaire se calcule sur la pente d'excès : ~2,73 G raw (35,7 h). Le run n'était pas « presque fini », il était à ~19 % du chemin.

**App Modal** : `ap-tFRss3VKGISdd7uu4fGoNK` → stopped, 0 tâche active

---

<a id="phase-2"></a>
## 2. Phase 2 — Diagnostic structurel : les caps GLAS

Le run initial n'a pas échoué sur un crossover mal estimé — il était **structurellement hors budget**.

**Chaîne causale** :
1. `factor_c175.sh` fixe le régime à **2 large primes** parce que le défaut 3LP (*« overflows glas's GPU buffers (ledger bake-off 4) »*)
2. Le 2LP force un `lim` élevé pour garder du rendement : `250M/600M`
3. Base de facteurs = π(250M) + π(600M) = **45,0 M de colonnes**
4. LA = 12,7 s/(M²) → **11 400–18 500 s** d'algèbre linéaire seule

**Correctif appliqué** :
- Création de `gpu/glas_caps_patch.py` : patch idempotent rendant les caps GLAS réglables par variables d'environnement
- Câblé dans le Dockerfile (COPY + chaîne de patches)
- Nouveaux knobs : `GLAS_BUCKET_MARGIN`, `GLAS_SURV_DIV`, `GLAS_HITS_DIV`, `GLAS_FCAND_MAX`
- Sans variable d'environnement : comportement bit-à-bit inchangé

**Règle de conception dérivée** : π(lim0) + π(lim1) ≤ 18 M pour que LA ≤ 3 000 s. `250/600` la viole d'un facteur 2,5.

---

<a id="phase-3"></a>
## 3. Phase 3 — Tests 3LP et caps (01/11 matin)

Build vérifié : patch appliqué, marqueurs présents dans le binaire, `nvcc -arch=sm_120` compile, `glas-gpu zmm/kmask insns: 0`.

### Run 3LP n°1
- **App** : `ap-HgwQGUp0iUkzmHlXYnb5Fw`
- **Config** : `lpb 32/32, mfb 64/99, lim 100M/130M, lambda 2.0352/2.8`
- **Caps** : margin 3, surv 16, hits 4, session ON
- **Résultat** : **0 relation GPU en ~20 min** ; co-crible CPU 358 rel/s ; 1 chunk CPU puis plus rien

### Run 3LP n°2
- **App** : `ap-O89QHSsTFO6lgmVTVMYJwp`
- **Config** : même N, `lpb 32/32, mfb 64/99, lim 100M/130M`
- **Caps** : margin 2, surv 32, hits 4, session OFF, PS 60 s
- **Résultat** : **0 relation GPU en ~8 min** ; co-crible CPU 347 rel/s

**Référence 2LP** : ~41 000 rel/s GPU.

**Verdict** : les caps n'étaient que le symptôme. Le coût du 3LP est dans le filtre à survivants (ECM sur cofacteurs ~2^75), pas dans la mémoire. ~100× plus lent que 2LP. **Le 3LP est une impasse logicielle.**

**Observation annexe** : le polyselect du run 1 s'est arrêté à MurphyE 7,73e-11 après 572 s, alors que son seuil `PS_ADAPT` (1,15e-9) n'a jamais été atteint — facteur ~15 sous la cible.

---

<a id="phase-4"></a>
## 4. Phase 4 — Balayage des régimes et loi de coût (01/11 après-midi)

Quatre runs instrumentés, même N (seed 12345). Tous mesurés sur la même bande de q `[2,2 M ; 2,4 M)`.

### 4.1 Le clamp du prédicteur (deux fois)

| run | `lim` | dernier raw | valeur annoncée | `last + 4×PROBE_STEP` |
|---|---|---|---|---|
| 2026-10-31 | 250/600 | 488 764 412 | 528 764 412 | 488 764 412 + 4×10 M ✓ |
| run A | 120/200 | 97 032 668 | 217 032 668 | 97 032 668 + 4×30 M ✓ |

Le prédicteur ne sait pas extrapoler au-delà de 4 pas. Ne jamais lire ce nombre comme un crossover.

### 4.2 Loi de complétion

Le point de production c169 (560 bits, terminé) : `lim 100/150` → FB 14,20 M, **420 M raw**, r = 29,6. Le nombre de relations à produire est **proportionnel au FB**.

### 4.3 Débit vs FB (polynôme non contrôlé)

| run | `lim` | FB | débit chunks 1-2 | MurphyE |
|---|---|---|---|---|
| c169 (560 b) | 100/150 | 14,20 M | 27 632 rel/s | — |
| run A | 120/200 | 17,92 M | 24 141 → 22 400 | 1,55e-10 |
| run B | 80/120 | 11,51 M | 21 012 → 20 996 | 5,92e-11 |
| run C | 40/60 | 5,99 M | **< 4 160** (bloqué) | 1,27e-11 |

### 4.4 Le FB gouverne le débit, pas l'appariement lim/lpb

Run H (`lpb 30/31, lim 48/67`) : 4 667 rel/s. Run I (`lpb 32/33, lim 48/67`) : 4 658 rel/s. Identique. La cause est la taille du FB : `débit ∝ FB^1,58`.

### 4.5 `ncurves` n'est pas un levier

Run K (`lim 120/200`, `ncurves 8` au lieu de 17) : 20 681 rel/s vs 21 206 (run J). −2,5 %, dans le bruit. GLAS est limité par le crible GPU, pas par le filtre ECM.

### 4.6 Modèle de coût (corrected — `STOP_LA_SCALE=1`, kappa=9,9)

| FB | `lim` | brut (r=29) | crible | LA | **total** |
|---|---|---|---|---|---|
| 6,87 M | 48/67 | 199 M | 27 071 | 659 | 29 030 |
| 10,0 M | 70/100 | 290 M | 21 767 | 1 397 | 24 464 |
| 14,0 M | 100/150 | 406 M | 17 902 | 2 139 | 21 940 |
| 17,92 M | 120/200 | 520 M | 15 511 | 3 505 | 20 105 |
| 22,0 M | 150/250 | 638 M | 13 768 | 5 283 | 20 164 |
| 45,0 M | 250/600 | 1 305 M | 9 085 | 28 287 | 38 672 |

Le minimum est ~20 000 s à `lim 120/200` — **1,48× le budget**.

---

<a id="phase-5"></a>
## 5. Phase 5 — Polyselect et polynôme P

### 5.1 Le polynôme vaut 1,6× de débit

Run D (MurphyE 1,71e-10) : 33 966 rel/s. Run J (MurphyE ~6e-11) : 21 206 rel/s. Même `lim 120/200`, même bande de q. **Le polynôme est le plus gros levier unitaire.**

### 5.2 Deux polyselects longs, deux tirages indépendants

| run | batchs | candidats | temps | MurphyE final |
|---|---|---|---|---|
| D | 20 | 46 797 | 1 381 s | 1,710e-10 |
| P | 40 | 93 679 | 2 858 s | 1,642e-10 |

Doubler le nombre de batchs ne donne **rien** (1,642 vs 1,710, soit 4 % en moins, dans le bruit). Le MurphyE plafonne à ~1,7e-10. Le seuil interne `PS_ADAPT` (1,15e-9) n'est pas calibré pour c175.

**Verdict** : le levier polynôme est épuisé. Ne plus y investir de temps.

### 5.3 Outillage créé

- `POLY_ONLY=/dev/stdout` : fait cracher le polynôme complet dans les logs
- `POLY_B64` dans `modal_rsa580.py` : réinjecte un polynôme via `POLY_IN` pour comparer deux régimes à polynôme fixe
- Polynôme P capturé : c5=1103760, skew 19723314.151, MurphyE 1.642e-10

### 5.4 `PS_ADAPT_MAXB` corrigé

Le défaut `PS_ADAPT_MAXB=6` silen­cieusement capait les runs à 6 batchs. Ajout des knobs PS_* à `ENV_EXACT` dans `modal_rsa580.py`. Vérifié : 20 et 40 batchs effectifs.

---

<a id="phase-6"></a>
## 6. Phase 6 — Correction majeure : le coude de débit (01/11 après-midi, §13)

> **Note** : cette section décrit une conclusion intermédiaire qui a été **réfutée** par la phase 7. Conservée pour la traçabilité.

À polynôme fixe (P), le débit n'est pas monotone en FB — il est **concave avec un coude vers F ≈ 10–12** :

| `lim` | FB | débit | brut (r=29) | crible | LA | total |
|---|---|---|---|---|---|---|
| 48/67 | 6,87 M | 4 658 | 199 M | — | — | (effondrement) |
| **70/100** | **10,0 M** | **26 380** | **290 M** | **10 993** | **1 091** | **13 385 s** |
| 80/120 | 11,5 M | 28 226 | 334 M | 11 826 | 1 446 | 14 572 s |
| 100/150 | 14,2 M | 29 614 | 412 M | 13 906 | 2 201 | 17 406 s |
| 120/200 | 17,92 M | 33 505 | 520 M | 15 511 | 3 505 | 20 316 s |

**Conclusion (alors)** : `lim 70/100` est optimal à 13 385 s, 7 % de marge.

**Pourquoi c'était faux** : tous les débits ont été mesurés sur la **première bande de q** `[2,2 M ; 2,4 M)` — la plus rapide. Le 27 632 rel/s de c169 est une **moyenne sur 420 M**. Comparer un instantané optimal à une moyenne de run complet surestime systématiquement les petits FB.

---

<a id="phase-7"></a>
## 7. Phase 7 — Reprise Modal, panne proxy, mesure décisive (01/11 soir)

### 7.1 Panne Modal : diagnostic complet

**Symptômes** après upgrade client 1.4.3 → 1.6.3 (imposé par `lol810-maxou2`) :
- `modal profile list` → tous les profils `Unknown (profile misconfigured)`
- `modal token info` → `Could not connect to the Modal server.`
- `~/.modal.toml` intact, se parsait correctement en Python

**Cause réelle** (trace Python) :
```
ImportError: A proxy is configured (http://127.0.0.1:50710) but the
'python-socks' package is not installed.
  -> ConnectionError("Could not connect to the Modal server.")
```

Le bac à sable exporte `HTTP_PROXY`/`HTTPS_PROXY` = `127.0.0.1:50710`. Modal 1.6.x honore ces variables (1.4.3 les ignorait). Refus sans `python-socks`.

**Correctif** : préfixer chaque appel par :
```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
    -u ALL_PROXY -u all_proxy
```

### 7.2 Second blocage : Python 3.10 supprimé de l'image builder 2026.10

```
Python 3.10 is not supported by the '2026.10' Image builder.
Set python_version to one of: ['3.11', '3.12', '3.13', '3.14', '3.14t', '3.15', '3.15t']
```

**Correctif** : `image=modal.Image.debian_slim(python_version="3.11")` sur la sonde. `modal_rsa580.py` non concerné (utilise `from_dockerfile`).

### 7.3 État des workspaces

| profil | état |
|---|---|
| `lol810-maxou2` | **OK** — 0,00 $ aujourd'hui |
| `lol810-maxou` | 42,67 $ dépensés, plafond atteint |
| `maxence81` | 0,00 $ mais plafond à 0 → refusé |
| `maxence7567`, `maxence-dabrowski81` | workspace en pause |

### 7.4 Limite confirmée par l'API publique

```
GET https://challenges.qbittensorlabs.com/v1/challenges/a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d
```

| milestone | bits | `max_solution_runtime` | statut | prix | soumissions |
|---|---|---|---|---|---|
| 340-bit | 340 | 14 400 | Complete | 10 000 $ | 4 |
| 460-bit | 460 | 14 400 | Complete | 10 000 $ | 59 |
| 480-bit | 480 | 14 400 | Complete | 10 000 $ | 33 |
| 500-bit | 500 | 14 400 | Complete | 20 000 $ | 47 |
| 512-bit | 512 | 14 400 | Complete | 20 000 $ | 5 |
| 530-bit | 530 | 14 400 | Complete | 10 000 $ | 1 |
| 560-bit | 560 | 14 400 | Complete | 20 000 $ | 30 |
| **580-bit** | **580** | **14 400** | **Incomplete** | **10 000 $** | **0** |

La limite est **par milestone**, dure, tuée par le validateur (`solution_container_manager.py:1083`). Le 560 a été résolu dans ces 14 400 s par un concurrent, alors que notre run c169 a mis 17 339 s — notre chaîne est ~20 % plus lente.

### 7.5 La mesure décisive : décroissance exponentielle du débit

Run `lim 70/100`, polynôme P, profil `lol810-maxou2`.

**Configuration lancée** :
```bash
RSA580_CPU_LAS=0 LPB0=32 LPB1=33 MFB0=64 MFB1=66
RLIM=70000000 ALIM=100000000 LAMBDA0=2.0352 LAMBDA1=2.0379
FIRST_PROBE=200000000 PROBE_STEP=40000000
POLY_B64="$(cat /tmp/polyP_b64.txt)"
```

**App** : `ap-glVtjqDySsFBeuBVxEtV5Q`

Démarrage confirmé : polynôme P injecté (`skew 19723314.151 c5 1103760`), base de facteurs construite (85,5 Mo), crible GPU lancé à 14:00:22.

**6 points de débit** :

| brut cumulé | débit (rel/s) |
|---|---|
| 3,35 M | 25 967 |
| 9,82 M | 25 591 |
| 17,52 M | 24 827 |
| 25,20 M | 24 226 |
| 32,93 M | 23 558 |
| 40,65 M | 22 910 |

Ajustement `ln(débit)` vs brut : pente **−0,00355 par M**, soit **3,55 % par 10 M**. Alignement quasi parfait sur 6 points. **Aucune saturation sur 40 M.**

Loi : `v(R) = 25 967 · exp(−0,00355 · R/M)`

Extrapolation au point de complétion (R = 29 × 9,88 = 286,5 M) : **~18 800 s de crible**, avant filtrage et LA.

### 7.6 Pourquoi le §13 se trompait

La décroissance dépend fortement de `lim`. En recalant le modèle sur c169 (`lim 100/150`, 420 M en 15 200 s), on trouve `k ≈ 0,00049 /M`, soit **7,3× moins** qu'à `lim 70/100`. Plus le FB est petit, plus le débit s'effondre vite. **« Prendre le plus petit FB possible » est la mauvaise stratégie.**

### 7.7 Le plancher sur tous les régimes 2LP

| `lim` | FB | brut | crible prédit | LA | total |
|---|---|---|---|---|---|
| 70/100 | 9,88 M | 286 M | **18 800 s** (mesuré) | 1 035 | 19 800 s |
| 80/120 | 11,46 M | 332 M | 16 100 s | 1 394 | 17 500 s |
| 100/150 | 14,41 M | 418 M | 15 650 s (calé c169) | 2 202 | 17 850 s |
| 120/200 | 17,87 M | 518 M | 15 900 s | 3 505 | 19 400 s |
| 135/230 | 20,0 M | 580 M | 18 300 s | 4 366 | 22 700 s |

Minimum : bassin plat ~15 500–16 000 s de crible + LA = **17 800–19 400 s**. Contre 14 400 s : **23 à 35 % au-dessus**. Filtrage non compté.

---

<a id="phase-8"></a>
## 8. Phase 8 — Essai 3LP final (01/11 soir)

La seule voie avec de la marge théorique : **3LP à petit `lim`** (6,84 M de colonnes, LA ~400–1 000 s).

**Configuration** :
```bash
LPB0=32 LPB1=33 MFB0=90 MFB1=92
RLIM=48000000 ALIM=67000000
LAMBDA0=2.81 LAMBDA1=2.79
GLAS_BUCKET_MARGIN=3 GLAS_SURV_DIV=16 GLAS_HITS_DIV=4
POLY_B64="$(cat /tmp/polyP_b64.txt)"
```

**App** : `ap-pugKXEX9NfGmmX9WzBlSMg`

**Résultat** : **19 minutes sans une seule relation**. Aucun message d'overflow, aucune erreur. Le run 2LP équivalent passe sa porte de relations en **132 s**.

Même mode d'échec silencieux que :
- `SIEVE_A=30` (44 min, 0 chunk) — la zone double déborde les bucket caps
- `GLAS_SURV_DIV=32` seul (75 min, 0 chunk)
- `GLAS_FCAND_MAX=4000000` → OOM CUDA franc (`src/sieve_core_gpu.cu:5156`, rc=134)

**Interprétation** : la cofactorisation du cribleur GPU ne scinde probablement pas un cofacteur en 3 premiers. Tous les candidats 3LP sont silencieusement jetés. Les caps agrandissent des buffers — ils n'ajoutent pas la capacité de factorisation manquante.

**Conclusion** : la 3LP est hors d'atteinte sur ce build. Les trois knobs de caps produisent tous le même blocage.

---

<a id="bilan"></a>
## 9. Bilan global des leviers testés

| levier | essais | configuration testée | résultat | verdict |
|---|---|---|---|---|
| `lim` (balayage complet) | 10+ runs | 48/67 → 135/230, 2LP | optimum ~15 500 s de crible | **> budget** |
| polynôme (MurphyE) | 2 longs | 20 batches (D) vs 40 batches (P) | 1,710e-10 vs 1,642e-10 | **saturé** (bruit) |
| `ncurves` | 1 run (K) | 8 au lieu de 17 | 20 681 vs 21 206 (−2,5 %) | **bruit** |
| caps GLAS `SURV_DIV=32` | 1 essai | seul, sans autres changements | 0 chunk en 75 min | **bloqué** |
| caps GLAS `FCAND_MAX=4M` | 2 essais | avec `SURV_DIV=16` | OOM CUDA (rc=134) | **OOM** |
| `SIEVE_A=30` | 1 essai | zone double | 0 chunk en 44 min | **bloqué** |
| 3LP (`mfb 90/92`) | 4 essais | `lim 48/67` et `100/130`, caps variés | **46,5 rel/s** (4,09 M candidats → 11 163 relations), GPU déborde à chaque q | **impasse mesurée** (§11.5) |
| décroissance du débit | 1 run mesuré | `lim 70/100`, 6 points sur 40,6 M | 3,55 %/10 M, non bornée | **réfute le §13** |
| co-crible CPU LAS | observé | tous runs | 700–800 rel/s | négligeable vs GPU |

---

<a id="verdict"></a>
## 10. Verdict et conditions de reprise

### Ce qui est prouvé

1. **La limite est 14 400 s, dure, par milestone** (API publique confirmée)
2. **Le plancher 2LP est ~17 800–19 400 s** (23–35 % au-dessus du budget, filtrage exclu)
3. **Aucun réglage de `lim` ne comble l'écart** (balayage complet de 48/67 à 135/230)
4. **La 3LP est bloquée** (0 relation, la cofactorisation GPU ne gère pas 3 premiers)
5. **Le polynôme est saturé** (MurphyE plafonne à ~1,7e-10, doubler l'effort ne change rien)
6. **Un concurrent a résolu le 560 dans 14 400 s** alors que notre chaîne met 17 339 s → nous sommes ~20 % plus lents

### Ce qu'il faudrait pour reprendre

1. **Un cribleur GPU qui gère la 3LP** — seule voie qui crée assez de marge (FB 6,84 M au lieu de 14,4 M)
2. **Ou ~35 % de débit en plus sur la 2LP** — qu'aucun réglage n'a donné
3. **Comprendre l'écart de 20 %** avec la chaîne qui a résolu le 560 dans le budget — c'est plus rentable que tout réglage de `lim`

### Dépenses

| session | workspace | montant |
|---|---|---|
| 31/10 | `lol810-maxou` | 42,67 $ |
| 01/11 soir | `lol810-maxou2` | 5,08 $ (2,76 $ run lim 70/100 + 2,32 $ essai 3LP) |

### Fichiers du projet

| fichier | rôle |
|---|---|
| `rsa580_solver/HANDOFF.md` | relay doc technique (15 sections) |
| `modal_rsa580.py` | runner Modal avec `POLY_B64`, `ENV_EXACT` étendu |
| `probe_profile.py` | sonde zéro-coût pour tester un workspace |
| `rsa580_solver/gpu/glas_caps_patch.py` | patch caps GLAS réglables |
| `rsa580_solver/pipeline_c169/factor_c175.sh` | pipeline principal |
| `rsa580_solver/pipeline_c169/factor_c169.sh` | pipeline 560-bit de référence |
| `/tmp/poly_P.txt` | polynôme P (c5 1103760, MurphyE 1.642e-10) |
| `/tmp/polyP_b64.txt` | polynôme P en base64 pour `POLY_B64` |

### Commande de lancement (si reprise)

```bash
cd /c/Users/maxen/enigma_rsa
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
    -u ALL_PROXY -u all_proxy \
RSA580_CPU_LAS=0 LPB0=32 LPB1=33 MFB0=64 MFB1=66 \
RLIM=70000000 ALIM=100000000 LAMBDA0=2.0352 LAMBDA1=2.0379 \
FIRST_PROBE=200000000 PROBE_STEP=40000000 \
POLY_B64="$(cat /tmp/polyP_b64.txt)" \
"C:/Users/maxen/AppData/Local/Programs/Python/Python310/python.exe" \
    -m modal run --detach ./modal_rsa580.py --difficulty 580 --seed 12345
```

> **Attention** : `modal run --detach` ne survit pas au SIGTERM du client. Toujours lancer en tâche de fond (`run_in_background`).

---

<a id="litterature"></a>
## 11. Revue de la littérature (02/11) — tri des sources et piste révélée

Une liste de références a été proposée. Elle a été **vérifiée une par une** (contenu réel, pas seulement existence) et croisée avec le code du solveur. Résultat : une référence majeure est hors sujet, deux sont réelles mais inexploitables, et une révèle une piste concrète que le journal avait mal qualifiée.

### 11.1 Tri des références

| Référence | Vérifié | Verdict |
|---|---|---|
| **Ducas, Stevens, van Woerden — *Advanced Lattice Sieving on GPUs, with Tensor Cores*** (ePrint 2021/141, EUROCRYPT 2021) | Réelle. Abstract : « GPU implementations of various state-of-the-art sieving algorithms for lattices … inside the **General Sieve Kernel (G6K)** … dimension 180 for the **SVP Darmstadt Challenge** » | **HORS SUJET.** C'est du *lattice sieving* au sens **SVP / crypto sur réseaux**, pas au sens NFS. Deux algorithmes sans rapport. Aucun Tensor Core ne peut accélérer GLAS : GLAS crible des paires (a,b) sur un corps de nombres, G6K cherche un vecteur court dans un réseau. **La liste l'annonçait comme « très pertinent pour optimiser glas » — c'est faux.** |
| **Miele, Bos, Kleinjung, Lenstra — *Cofactorization on Graphics Processing Units*** (ePrint 2014/397, CHES 2014) | Réelle. « the cofactorization step … can be farmed out to a GPU … can serve as a cryptanalytic co-processor for several Intel i7-3770K quad-core CPUs simultaneously » | **Réelle et pertinente**, mais pour l'**architecture**, pas pour nos réglages : le GPU y fait la cofactorisation pendant que les CPU criblent. C'est l'inverse de notre montage. Elle ne traite pas la limite 2LP/3LP. |
| **McGuire & Robinson — *A New Angle on Lattice Sieving for the NFS*** (arXiv 2001.10860) | Réelle. « lattice enumeration in three dimensions … successive minima and shortest vectors … record in a 133-bit subgroup of Fp6 … nearly 3 times faster » | **Réelle et pertinente en principe** : énumération 3D au lieu des vecteurs de transition. Mais le gain est mesuré sur un corps de 423 bits (petit), et GLAS crible en 2D. Inexploitable sans réécrire le cœur du cribleur. |
| **pstach/gls — GPU Lattice Siever** | Réel, OpenCL, LGPL. Le README dit lui-même : « **the overall runtime is not as fast as say CADO's lattice siever** … initial implementation … tested on nVidia 600 and 700 GPUs » | **Inutilisable.** Prototype OpenCL de 2011, plus lent que le cribleur CPU de CADO. Ce n'est pas une référence de performance. |
| Barbulescu & Lachand (arXiv 1403.0184) | Réelle | Théorie de Murphy α/E. Ne bat pas la recherche pratique de CADO (déjà saturée, cf. §5). |
| Kleinjung, SHARCS 2006 | Réelle | Stratégies de cofactorisation. Conceptuellement juste, mais antérieure à la pratique 3LP. |
| Paramètres CADO officiels | Réels | **C'est la référence la plus utile de la liste** — voir 11.2. |

**Correction principale à retenir** : la référence présentée comme la plus importante (Tensor Cores / 2021/141) est sans rapport avec le problème. Ne pas y consacrer de temps.

### 11.2 Ce que la liste révèle réellement : la 3LP n'est pas exotique, c'est la recette standard

La recette **c175 officielle de CADO**, déjà présente dans l'arbre (`third_party/cado-nfs-public/gpu-siever/params/params.c175`) :

```
lim0=48.1M lim1=67.6M lpb0=30 lpb1=31 mfb0=60 mfb1=90
```

`mfb1 = 90` avec `lpb1 = 31` signifie **3 grands premiers** côté algébrique (3 × 31 ≈ 93 ≥ 90). Donc **le régime 3LP est la norme à c175**, et notre 2LP (`mfb 63/65`) est le compromis imposé par GLAS.

Cela recadre tout le problème. Le journal §15 concluait « la 3LP est une impasse logicielle ». La formulation correcte, après lecture du code, est plus précise et plus utile :

> Le régime qui rend c175 faisable est la 3LP. Nos trois cribleurs sont chacun disqualifiés **pour une raison mesurée et distincte**, pas par une impossibilité de principe.

### 11.3 État vérifié des trois cribleurs (dans le code, pas supposé)

| cribleur | présent dans l'image ? | 3LP ? | mesure |
|---|---|---|---|
| `glas` (GPU) | oui, production | **non** — 0 relation en 19 min, sans erreur | §15.5 |
| `bench` = cuda-sieve (GPU, queue ECM) | **NON** — `Dockerfile:10` : « The cuda-sieve/gchilders bench and cofac_cpu (SIEVER=bench only) were **dropped 2026-10-25** » ; le dossier `cuda-sieve/` **n'est plus vendored** | oui (il avait `--cofactor` + queue ECM) | **indisponible** : il faudrait re-vendoriser tout l'arbre |
| `las` (CPU CADO) | oui — `Dockerfile:84` copie `sieve/las` dans `/app/cado-filter/` | **oui**, via `facul` (3LP natif) | **trop lent** : `factor_c175.sh:379` mesure **626 rel/s à `-t 14`** à c160 ; à c175, ~400-600 rel/s sur 24 threads, contre 30 000 nécessaires → **~50-60× trop lent** |

**Conclusion** : `bench` est perdu (source non vendored), `las` est structurellement trop lent d'un facteur ~50. Il ne reste que `glas`, qui est le seul assez rapide **et** le seul incapable de 3LP.

### 11.4 La piste que la lecture du code ouvre : GLAS a déjà la machinerie

Contrairement à ce que le §15 supposait (« la cofactorisation GPU ne scinde pas en 3 premiers »), le source de GLAS montre que :

- la cofactorisation **n'est pas faite sur le GPU** mais sur l'hôte, par **`facul`** (bibliothèque ECM de CADO) : `cofactor_cpu()`, `cofactor_finish()`, `facul_all()` (`src/glas.cpp:1276-1310`) ;
- la logique de comptage des grands premiers **existe** : `for (klpb = lpb; klpb < s; klpb += lpb)` (`:1056-1057`), et le rejet se fait sur `mfb + marge` (`:909-922`) ;
- il existe même un **hook de diagnostic jamais câblé** : `GLAS_COFAC_DUMP=path` (`:1090-1130`), qui écrit chaque paire de cofacteurs résiduels avant `facul`.

Donc l'échec 3LP n'est **pas** un manque de logique. L'explication la plus probable, et celle que la littérature (Kleinjung ; Miele et al.) désigne, est un **effondrement du coût de `facul`** : un résidu de ~2^85-2^90 exige beaucoup de courbes ECM par candidat, le chunk ne se termine jamais, et l'on observe « 0 relation, aucune erreur » — exactement le symptôme mesuré.

**C'est la distinction qui compte** : « logique absente » = impasse définitive ; « coût ECM qui explose » = peut-être réglable. Le journal n'avait jamais tranché entre les deux.

### 11.5 Le test décisif — exécuté le 02/11, résultat sans ambiguïté

Le hook `GLAS_COFAC_DUMP` a été branché (`diag_3lp_cofac.py`, app `ap-h4hBlkVCgz6S1vJOjkaGNu`, 240 s de crible, `lim 48/67 mfb 90/92`, polynôme P, même bande `q ∈ [2,2 M ; 2,4 M)` que les mesures 2LP).

**Trois mesures, une seule conclusion.**

**(a) Le GPU déborde à chaque q — et les caps sont déjà énormes.**

```
# GPU overflow at q=2200717 (caps surv=8388608 hits=67108864); falling back to CPU
```

36 événements d'overflow sur 22 q distincts en 240 s, avec `surv = 8 388 608` (2^23) et `hits = 67 108 864` (2^26) — c'est-à-dire les caps **par défaut**, déjà à 8,4 M de survivants. Et ça déborde quand même. La raison est visible dans le log :

```
# Sieving side-1 q=2200013; ... 1718805 survivors
```

**1,72 M de survivants pour un seul q** (contre quelques dizaines de milliers en 2LP). Avec `mfb=90`, le critère d'acceptation `r = min(lambda·lpb, mfb+8) ≈ 90 bits` est si permissif que la population de survivants explose. Aucun cap raisonnable ne la contient : c'est structurel, pas un réglage.

**(b) Le repli CPU donne 46 rel/s — 100× trop lent.**

| | 2LP `lim 48/67` (run I) | 3LP `lim 48/67` (ce test) |
|---|---|---|
| relations en 240 s | ~1,12 M (4 658 rel/s) | **11 163** |
| débit | 4 658 rel/s | **46,5 rel/s** |

Le GPU étant en repli CPU sur presque tous les q, le débit s'effondre. À 46,5 rel/s, les 199 M de relations nécessaires prendraient **4,26 M s ≈ 49 jours**.

**(c) `facul` n'accepte que 0,27 % des candidats.**

4 094 586 candidats produits → 11 163 relations. Distribution des résiduels mesurée par `tools/cofac_dump_stats.py` :

| côté | médiane | p90 | max | ≤ 2·lpb | ≤ 3·lpb |
|---|---|---|---|---|---|
| 0 (rationnel) | **84 b** | 89 b | 90 b | 10,2 % | 89,8 % |
| 1 (algébrique) | **87 b** | 92 b | 92 b | 5,4 % | 94,6 % |

Les résiduels sont bien à 84-92 bits, donc 3LP comme prévu. Mais avec `ncurves=17` — valeur calibrée pour la 2LP — `facul` n'arrive à scinder que 0,27 % d'entre eux. Le coût ECM par candidat est bien le mur annoncé.

**Verdict.** L'hypothèse « la cofactorisation GPU ne scinde pas en 3 premiers » est **fausse** : la cofactorisation est sur l'hôte, elle reçoit bien les candidats, et elle en accepte quelques-uns. Le blocage est **double et cumulatif** : (1) le GPU déborde structurellement à `mfb=90` et retombe sur un repli CPU à 46 rel/s ; (2) `facul` à `ncurves=17` est très en dessous du régime 3LP. Le premier point suffit à condamner la 3LP sur GLAS, indépendamment du second.

| médiane des résidus | ce que ça aurait voulu dire | ce qu'on a mesuré |
|---|---|---|
| ≤ 65 b → réglable | — | — |
| ≥ 85 b → coût ECM = mur | ✔ | **84-87 b, 0,27 % d'acceptation** |
| 0 candidat → rejet en amont | — | 4,09 M candidats, donc rejet **après** |


### 11.6 Pourquoi le découplage crible/cofactorisation ne suffirait pas

C'était l'idée tirée du papier 2014/397, et le test la disqualifie comme remède principal. Découpler la cofactorisation ne traite que le point (c) — `facul` à `ncurves=17`. Or le point (a) est **en amont** : le GPU déborde et ne produit ses survivants qu'en repli CPU. Même avec une cofactorisation parfaite et gratuite, on resterait à ~46 rel/s côté crible.

Pour rouvrir la 3LP il faudrait donc **d'abord** que le cribleur GPU tienne 1,7 M de survivants par q sans déborder, ce qui suppose une refonte du buffer de survivants (dimensionné par bande, pas par q) — pas un changement de paramètre. Le découplage ne viendrait qu'**après**, en second.

Autrement dit, la voie existe théoriquement mais elle demande deux chantiers successifs sur le cribleur, et le premier n'est pas dans nos moyens actuels : `GLAS` est un binaire Cognition patché, pas un projet que l'on peut refondre.

### 11.7 Ce que la littérature ne donne pas


Pour être clair sur les attentes :

- **Aucun gain de débit sur GLAS** ne viendra de ces papiers. Le cribleur est déjà patché (7 patches de perf dans le Dockerfile, gains mesurés de 1 à 8 % chacun) et le débit est limité par le matériel.
- **Aucun meilleur polynôme** : Barbulescu-Lachand est théorique, et CADO sature à 1,7e-10 (§5).
- **Aucun gain d'algèbre linéaire** : LA est à 3 505 s à `lim 120/200`, et le block-Lanczos GPU est déjà en place.

La littérature ne sert qu'à **une** chose ici : confirmer que la 3LP est le bon régime, et indiquer comment diagnostiquer pourquoi elle échoue chez nous.

### 11.8 Verdict révisé

Le verdict du §10 tient, mais sa formulation change — et la mesure du 02/11 referme la porte que la lecture du code avait entrouverte :

| avant (§10) | après (§11) |
|---|---|
| « la 3LP est une impasse logicielle » | « la 3LP est le **bon** régime, mais GLAS déborde structurellement à `mfb=90` : 1,7 M de survivants par q, repli CPU, **46 rel/s** contre 4 658 en 2LP » |
| « la cofactorisation GPU ne scinde pas en 3 premiers » | **faux** : elle est sur l'hôte, elle reçoit 4,09 M candidats et en accepte 0,27 % ; le coût ECM est le second mur, pas le premier |
| « aucun levier ne reste » | « aucun levier **de réglage** ne reste ; il resterait une refonte du buffer de survivants de GLAS, hors de portée » |
| « il faudrait ~1,35× le débit » | inchangé : ~1,35× en 2LP, et la 3LP n'offre pas cette marge puisqu'elle est 100× plus lente |

Ce qui n'a pas changé et qui reste le cœur du dossier : **aucun réglage de `lim`, de polynôme, de `ncurves` ou de caps ne sauve la 2LP**, et la 3LP — seule alternative — est mesurée à 46 rel/s. Le budget de 14 400 s n'est atteignable par aucune des deux voies avec les outils actuels.

**Ce que le test a coûté** : un run de 5 min, ~0,05 $. C'est le meilleur rapport information/coût de tout le projet — il a transformé une hypothèse (« la cofactorisation GPU ne scinde pas en 3 ») en un diagnostic chiffré à trois composantes, et il a évité de lancer un run 3LP de 4 h qui aurait échoué.

---

<a id="mcguire"></a>
## 12. McGuire-Robinson (arXiv 2001.10860) — évalué, écarté

Question posée : *« ça vaudrait le coup de tester McGuire-Robinson ? personne ne l'a fait dans les challenges précédents ? »* Réponse vérifiée dans le code, pas par intuition.

### 12.1 Ce que le papier propose réellement

> « a different method of lattice **enumeration in three dimensions** … We use the **successive minima and shortest vectors** of the lattice instead of **transition vectors** … record computation in a 133-bit subgroup of Fp6 … nearly 3 times faster … generalizes to dimensions 4 or more, overcoming a key obstruction to the implementation of the **tower number field sieve**. »

C'est une amélioration de l'**énumération des points du réseau**, pas du crible lui-même. Elle remplace les vecteurs de transition de Franke-Kleinjung par les minima successifs, et son intérêt réel est de rendre viable l'énumération en **dimension ≥ 3** — ce qui sert à deux choses : le tower NFS, et le **crible à deux special-q simultanés** (double large prime), où le réseau est de dimension 3.

### 12.2 Personne ne l'utilise — vérifié, pas supposé

| code | énumération | source |
|---|---|---|
| CADO-NFS (arbre vendored) | **Franke-Kleinjung 2D** | `sieve/las-plattice.hpp:441` — « enumerating lattice points with the Franke-Kleinjung algorithm » ; **aucune** occurrence de « successive minima » dans tout l'arbre |
| GLAS (Cognition) | **2D**, base de réseau par `SkewGauss` par special-q | `src/glas.cpp:5` ; repli CPU en Franke-Kleinjung (`sieve_core_cpu.cpp:4`) |
| 500 bits (Xdev, gagnant) | **Franke-Kleinjung 2D** | `gpu_loop.cu:1280` — « Franke-Kleinjung "sieving by vectors" » |
| 460 / 480 bits | même lignée `gpu_loop` | README du dépôt officiel |
| 340 bits | YAFU SIQS (CPU) — même pas du NFS | idem |

**Aucune implémentation de production du NFS n'utilise McGuire-Robinson**, et aucun gagnant du challenge non plus. Le dépôt officiel des solutions ne publie d'ailleurs que jusqu'au 500 bits : les sources des 512, 530 et 560 n'ont jamais été publiées.

### 12.3 Pourquoi ça ne viserait pas notre blocage

Nos deux problèmes mesurés (§15, §11.5) sont :

1. **2LP** : il manque ~1,35× de débit. Le goulot est le remplissage des buckets et le filtre à survivants sur GPU — pas l'énumération.
2. **3LP** : 1,72 M de survivants par q font déborder le buffer. C'est une conséquence de la borne `mfb=90`, sans rapport avec l'énumération.

McGuire-Robinson accélère l'énumération. Elle ne réduit ni le nombre de survivants, ni le coût du filtre, ni la taille de la base de facteurs — les trois termes qui décident de notre budget. Le gain à en attendre ici est indirect et non quantifié.

### 12.4 Ce que ça coûterait

GLAS est un binaire Cognition que l'on patche par remplacement de chaînes (7 patches, gains mesurés de 1 à 8 %). En changer le cœur d'énumération, c'est **écrire un cribleur**, pas le régler — et pour la variante qui en tirerait parti (2 special-q simultanés) il faudrait en plus une structure de buckets en 3D et une gestion de survivants nouvelle. À titre d'ordre de grandeur, `gpu_loop.cu` du gagnant fait **187 Ko de CUDA** pour un cribleur **2D**.

Face à un déficit de 20-35 % et à un gain spéculatif, ce n'est pas le bon investissement. **Écarté.**

### 12.5 Ce qui serait le bon investissement

Comprendre pourquoi notre chaîne met 17 339 s sur le 560 là où un concurrent a tenu dans 14 400 s. C'est 20 % d'écart, mesuré, sur un cas **déjà résolu** — donc nécessairement atteignable. Le code n'étant pas publié, la piste est un write-up externe, pas une lecture de source.

---

<a id="phase-9"></a>
## 13. Phase 9 — Le dernier levier (nombre de GPU) et clôture définitive (02/11)

Cette phase ne contient aucun run : elle ferme le seul levier qui restait ouvert,
par la **spécification** du validateur et par un recoupement de chiffres.

### 13.1 La spécification du validateur

Documentation officielle du challenge, section *Validation Environment* :

| ressource | valeur |
|---|---|
| GPU | **NVIDIA RTX PRO 6000, 96 GB VRAM** — *un seul*, au singulier |
| CPU | 24 vCPU |
| RAM | 85 GB |
| Wall time | 4 hours (conteneur tué à cette limite) |
| Isolation | aucun réseau, aucun accès aux ressources de l'hôte au-delà de CPU, GPU, mémoire |

### 13.2 Ce que ça ferme : le débit ne peut pas être multiplié

Le crible représente ~85 % du temps total. Il fallait **≥ 1,49×** d'agrégat pour
ramener les ~19 400 s de crible sous les ~13 000 s disponibles (§13.3). Un
partage sur deux devices était la seule façon d'obtenir ce facteur sans toucher
aux mathématiques.

Deux verrous, tous deux définitifs :

1. **Un seul GPU est alloué.** `--gpus all` dans la commande de run ne donne que
   ce que le nœud possède ; la spec provisionne *un* RTX PRO 6000.
2. **La chaîne n'en utiliserait qu'un de toute façon.** `factor_c175.sh:196` :
   *« ONE glas process for the whole sieve (FB, CUDA context, device/pinned
   buffers, strategies initialised once) »*. `nvidia-smi -L` n'y sert que de
   test d'existence (ligne 541), jamais à compter les devices. Aucun chemin de
   code ne sharde les bandes q sur plusieurs processus.

Le levier multi-GPU est donc mort **par spécification**, et le test que
j'envisageais (deux instances sur `RTX-PRO-6000:2`) aurait mesuré un
environnement que le validateur ne fournit pas. Il n'a pas été lancé.

### 13.3 Le vrai chiffrage : le besoin est fixé par `lpb`, pas par `lim`

> **Correction du 2026-11-02, après revue contradictoire.** La première version
> de cette section affirmait que le 560 et le 580 partageaient `lim 100M/150M`,
> donc la même base de facteurs, donc le même besoin en relations. **C'est faux.**
> La « validation » de la loi `raw ≈ 30 × FB` qui en découlait était circulaire.
> Le chiffrage correct est ci-dessous : il donne un résultat voisin, mais pour
> une autre raison, et avec une précision moindre.

**Ce que le 560 expédié utilise vraiment.** `SUBMISSION_INFO.txt` ne mentionne
aucun `lim` : il dit seulement « `factor_c169.sh` defaults under `CONTAINER=1`,
`RSA560_LPB1=33` ». Le `Dockerfile` du 560 ne fixe **ni `RLIM` ni `ALIM`** (seule
une ligne `ALIM=600M` est commentée, ligne 137). Les défauts effectifs sont donc
ceux de `factor_c169.sh:170` :

```
RLIM=${RLIM:-200000000}; ALIM=${ALIM:-450000000}
# lim 200M/450M: +8.8% / +13.4% / +15.1% rel/s at q 2.2M / 12.5M / 22.4M vs 100M/150M
```

Soit **`lim 200M/450M`**, et non 100M/150M. Le commentaire « ~420M raw relations »
de `factor_c175.sh:212` décrit un profil **antérieur** ; son commentaire d'origine
le dit lui-même : « *the 530 lims 100M/150M* » (profil du 2026-10-17).

**Ce qui fixe réellement le besoin.** La table `XOVER` de `stop_cost.py:196-198` :

```
XOVER = {(31,32): (293e6,'measured'), (31,33): (366e6,'measured'),
         (32,33): (441e6,'measured'), (32,34): (514e6,'model'), ...}
```

avec la note décisive des lignes 193-195 : *« the crossover is a property of the
regime, not of the key … **lim/lambda variants reach the same count sooner (same
relations needed)** »*.

Autrement dit : **le besoin est indexé par `lpb`, pas par `lim`.** À 32/33 il vaut
**441 M** au croisement, et **485 M** de relations brutes sur la clé mesurée
(`factor_c169.sh:70`). Le 580, à `lpb 32/33`, a donc bien le même besoin que le
560 — mais parce que le **régime de grands premiers** est partagé, pas parce que
le `lim` l'est.

**Ce que la correction détruit.** La « validation » précédente comparait un
comptage *brut* du profil 530 (420 M) à la FB de ce même profil (14,03 M) pour en
tirer `r ≈ 30`, puis l'appliquait comme une loi universelle. Le point indépendant
donne tout autre chose :

```
FB(200M/450M) = π(2·10⁸) + π(4,5·10⁸) = 11 078 937 + 23 846 000 ≈ 34,92 M
croisement 441 M / 34,92 M = 12,6        brut 485 M / 34,92 M = 13,9
```

**`r ≈ 13`, pas 30.** La constante n'est donc pas universelle : elle dépend du
régime. La loi `raw ≈ 30 × FB` du §10 est **retirée** — elle n'était valable que
pour le profil 530 à `lim 100M/150M`.

**Le budget, recalculé proprement.** Le besoin étant fixé (441 M au croisement,
485 M brut), seule la vitesse reste à estimer, et elle dépend du `lim` :

| config | débit | crible à 485 M | LA | total |
|---|---|---|---|---|
| `lim 100M/150M` (défaut 580) | 24 973 rel/s (mesuré) | 19 420 s | faible (FB 14,03 M) | **~20 800 s** |
| `lim 200M/450M` (config 560) | +8,8 à +15,1 % → ~27 200–28 700 | 16 900–17 800 s | ~2 200 s (coût post-crible mesuré du 560) | **~20 400 s** |

Les deux configs atterrissent au même endroit, **~20 400–20 800 s** : le gain de
débit du grand `lim` est absorbé par l'algèbre linéaire, dont le coût croît comme
`FB²`. C'est d'ailleurs pourquoi le balayage du §4 avait retenu 100M/150M pour
le 580.

```
total ≈ 20 400 à 20 800 s   contre   14 400 s
dépassement ≈ +42 à +44 %
accélération nécessaire ≈ 1,42 à 1,44×
```

> **Ce que je retire** : le « 19 918 s / +38,3 % / 1,38× » de la version
> précédente. Il reposait sur 420 M (profil 530) au lieu de 485 M, et sur un
> partage crible/LA du 560 supposé. Le chiffre correct est **~20 600 s, +43 %**,
> avec une bande d'incertitude honnête de **19 000 à 24 000 s** (décroissance de
> débit sur un run complet, besoin réel à c175, coût exact de la LA).
>
> **⚠ Ce chiffre est lui aussi périmé** — le run du §14 a mesuré **23 244 à
> 23 942 s (+61 à +66 %)**. La bande de 19 000–24 000 s contenait la vérité en son
> haut, pas en son milieu : la décroissance réelle du débit est ~3× plus raide
> que celle extrapolée.
>
> **Ce que je retire aussi** : la « pénalité de 1,44× » présentée comme mesurée.
> C'était une **inférence** : elle suppose que le run 560 a consommé ~900 s de
> polyselect et ~2 200 s de LA, ce qui n'est pas instrumenté dans les notes. Le
> rapport 24 973 / ~41 000 reste plausible, mais il compare un débit mesuré sur
> 900 s à un débit déduit d'un total — deux natures différentes. Le §6 du README
> avait justement identifié ce piège ; je l'ai reproduit.

### 13.4 Pourquoi le 14 774 s ne contredit pas la limite de 14 400 s

Cette contradiction apparente traînait dans mes notes ; elle est levée :

1. **14 774 s n'est pas une soumission validée.** C'est une mesure *blind GCP*
   (`gpu/key1m.env`, commentaire `factor_c169.sh:73`) — un run de développement
   sur une clé dont la factorisation était inconnue, hors validateur.
2. **Le 560 était budgété à ≤ 13 000 s**, pas 14 400 (`breaking_rsa.py:261-263`,
   `FULL_RUN_SECS`). Le 14 774 s est donc déjà **au-dessus** de sa propre cible.
3. **La grâce réelle du validateur est de ~30 s**, pas 5 min :
   `SOLUTION_CONTAINER_MANAGER_TIMEOUT = 30` (`qbittensor/constants.py:32`),
   vérifié le 2026-09-11 après un `WALL_TIME_FAILURE`. Le docstring de
   `hard_wall()` corrige explicitement l'ancienne affirmation « jusqu'à 5 min »,
   qui surestimait la marge d'un facteur ~10.

Autrement dit : **notre chaîne était déjà marginale sur le 560**, et le 580 est
strictement plus dur. Il n'y a aucune marge cachée à récupérer.

### 13.5 Tableau de clôture

| levier | statut | preuve |
|---|---|---|
| `lim` (48/67 → 135/230) | fermé | 10+ runs, plancher ~15 500–16 000 s de crible |
| polynôme / MurphyE | fermé | saturé 1,710e-10 vs 1,642e-10 ; ropt + sopt **déjà actifs** (`SOPT_EFF=9`, `SOPT_K=500`) |
| `ncurves` 8 vs 17 | fermé | −2,5 %, dans le bruit |
| caps GLAS (margin/surv/hits/fcand) | fermé | OOM CUDA ou 0 relation |
| `SIEVE_A=30` | fermé | 0 chunk en 44 min |
| profil de threads (`-t 16` vs `-t 20`) | fermé | ratio **exactement 1,000** |
| `GLAS_ADJUST` | **gagné** | 1,434× — déjà `=3` par défaut dans le pipeline |
| `GLAS_ADJUST_SQUEEZE` | **gagné** | +4,8 % — adopté à `=3` le 02/11 |
| 3LP (`mfb 90/92`) | fermé | **46,5 rel/s**, GPU déborde à chaque q, 199 M rel → ~49 jours |
| McGuire-Robinson | fermé | accélère l'énumération, pas le filtre à survivants (§12) |
| **nombre de GPU** | **fermé (spec)** | **1 seul RTX PRO 6000 alloué** ; la chaîne n'en piloterait qu'un |
| grâce du validateur | fermé | ~30 s, mesuré |

### 13.6 Verdict — remplacé par le §14

> **Cette section est périmée.** Elle concluait « très probablement hors de
> portée, déficit ~1,43× (≈20 600 s) », en laissant trois inconnues ouvertes. Le
> run du **§14** les a tranchées le 2026-11-02 : déficit **1,45× en relations**,
> total **23 244–23 942 s**, soit **+61 à +66 %**. Le chiffre est plus mauvais que
> celui annoncé ici, et il est mesuré. La liste des leviers fermés (§13.5) reste
> valable.

Ce que le §14 a effectivement levé, parmi les trois inconnues listées ici :

1. **le besoin réel à c175** — non mesuré directement (le run a été arrêté avant
   le croisement), mais borné : le besoin est ≥ 441 M, et le budget n'en produit
   que ~304 M. Le doute n'a plus d'effet sur la conclusion ;
2. **la décroissance du débit** — **mesurée** : −133 rel/s par chunk, moyenne
   cumulée 22 194 rel/s. C'est ce qui a fait passer le total de 20 600 à ~23 900 s ;
3. **le coût de la LA** — toujours non mesuré, et désormais sans importance : même
   à zéro, le crible seul dépasse le budget de 46 %.

Le seul gain réel de la session reste `GLAS_ADJUST_SQUEEZE=3` (+4,8 %), adopté.

### 13.7 Ce qui rouvrirait le dossier

Trois conditions, par ordre de plausibilité :

1. **Un cribleur GPU capable de 3LP** — c'est-à-dire avec un buffer de survivants
   qui ne déborde pas à 1,72 M par q. Ce n'est pas un réglage de GLAS : c'est un
   autre binaire. Gain attendu : le régime 3LP divise le besoin en relations par
   ~2,5, ce qui remettrait le 580 largement sous le budget.
2. **Une machine à plusieurs GPU** — ~1,5× sur le crible suffit. Le code actuel
   ne sharde pas ; il faudrait router les bandes q sur N sessions FIFO
   (`i mod N`) et remplacer le test d'existence `nvidia-smi -L` par un comptage.
   Sans regret : repli sur un device si un seul est visible.
3. **Comprendre l'écart de 20 % avec le concurrent sur le 560** (§12.5) — piste
   la plus faible, car même comblée intégralement elle ne donne que 1,20×,
   contre ~1,6× requis (§14).

### 13.8 Journal des corrections (2026-11-02)

Une revue contradictoire a relevé quatre erreurs dans la première version de ce
§13. Elles sont toutes fondées, et corrigées ci-dessus :

| affirmation initiale | statut | réalité |
|---|---|---|
| « le 560 expédié tourne à `lim 100M/150M` » | **faux** | `Dockerfile` 560 sans `RLIM`/`ALIM` → défaut `factor_c169.sh:170` = **200M/450M** |
| « le 420 M vient de `factor_c175.sh:212` » | **mal lu** | ce commentaire décrit le profil **530** du 17/10 (« the 530 lims 100M/150M ») |
| « `420/14,03 = 29,9` valide `raw ≈ 30 × FB` » | **circulaire** | point indépendant : 441 M à FB 34,92 M ⇒ **r ≈ 13** |
| « pénalité de 1,44×, mesurée » | **inférence** | compare un débit sur 900 s à un débit déduit d'un total |

Deux erreurs de forme, également corrigées : le dépôt est **public** (l'API
répond 200 en anonyme), et le §6.3 du README confondait le code du concurrent
(non publié) avec `rsa560_solver/`, qui est bien dans le dépôt et exécutable.

La conclusion survit à la correction — les deux configs atterrissent à
~20 400–20 800 s — mais la précision affichée (« 19 918 s », « +38,3 % »,
« 1,38× ») était illusoire. **C'est le principal enseignement de cette phase :
un chiffrage à quatre chiffres significatifs bâti sur deux hypothèses non
mesurées n'est pas un chiffrage, c'est une conjecture habillée.**

> **Suite (§14)** : le run de mesure a confirmé le diagnostic mais **aggravé le
> chiffre** — 23 244 à 23 942 s, pas 20 400–20 800. La cause est identifiée : la
> pente de décroissance du débit à `lim 200M/450M` est ~3× plus raide que celle
> extrapolée depuis `100M/150M`. L'erreur de méthode est la même que celle
> dénoncée ci-dessus, une couche plus bas : une pente mesurée sur un régime ne
> vaut pas pour un autre.

---

<a id="phase-10"></a>
## 14. Phase 10 — Le run qui tranche : mesure directe du profil 560 sur c175 (02/11)

### 14.1 Pourquoi ce run

Le §13 chiffrait le 580 par arithmétique : besoin en relations × débit mesuré. Une
revue contradictoire a objecté, à juste titre, que ce chiffrage reposait sur deux
hypothèses non mesurées (le besoin réel à c175, et la décroissance du débit sur
5 h). Le seul moyen de trancher était de **faire tourner la chaîne gagnante du 560
sur le N de 580 bits** et de lire un temps total.

Config retenue : celle du 560 **expédié**, c'est-à-dire les défauts de
`factor_c169.sh:170` que son `Dockerfile` n'écrase pas. Bannière réellement
émise au démarrage, qui confirme les trois surcharges :

```
### c169 GNFS: 175 digits, 20 CPUs, siever glas, lpb 32/33 mfb 62/64
    lim 200000000/450000000 A 29 lambda 2.0352/2.0379 ncurves 17/17 -t 4 qmin 2200000
### [3/4] GPU lattice sieve + concurrent CADO probes (first probe at 450000000 raw)
```

`MFB0=62 MFB1=64` et `RLIM=200M ALIM=450M` ont bien pris (les variables explicites
priment sur les `RSA580_*` du `Dockerfile`). `LAMBDA0/1` n'avaient pas à être
imposés : `RSA580_LPB1=33` les déclenche déjà à `2.0352/2.0379` dans les deux
chaînes. `FIRST_PROBE=450M` explicite a gagné sur `FIRST_PROBE_AUTO` (l'auto ne
s'applique que si la variable est vide, `factor_c175.sh:239`). `WALL_TIME` laissé
non fixé ⇒ `wall_budget()` renvoie `None` ⇒ run relation-borné, jamais suicidé.
Watchdog de télémétrie neutralisé (`TELEMETRY=0`, deadlines à 26 000 s), sinon
`os._exit()` à 14 385 s.

Durée : 3 h 54 de mur, dont ~40 min de reconstruction d'image. Coût ~9–10 $.
Run interrompu volontairement à 12 160 s de crible, une fois la conclusion
acquise — la sonde à 450 M n'a pas été atteinte.

### 14.2 Le débit, chunk par chunk

Démarrage du crible 08:17:10 UTC, pré-crible (polyselect + makefb) 574 s.

| chunk | rel/s | chunk | rel/s | chunk | rel/s |
|---|---|---|---|---|---|
| 1 | 24 268 | 13 | 23 659 | 25 | 21 885 |
| 2 | 23 749 | 14 | 23 197 | 26 | 21 716 |
| 3 | 26 887 | 15 | 22 768 | 27 | 21 570 |
| **4** | **27 658** (pic) | 16 | 22 361 | 28 | 21 414 |
| 5 | 27 217 | 17 | 21 949 | 29 | 21 335 |
| 6 | 26 793 | 18 | 21 550 | 30 | 21 159 |
| 7 | 26 241 | 19 | 21 156 | 31 | 20 990 |
| 8 | 25 733 | 20 | 20 787 | 32 | 20 868 |
| 9 | 25 314 | 21 | 20 594 | 33 | 20 714 |
| 10 | 24 906 | 22 | 22 299 | 34 | 20 591 |
| 11 | 24 509 | 23 | 22 184 | | |
| 12 | 24 014 | 24 | 21 923 | | |

**Pente mesurée sur les 11 derniers chunks : −133 rel/s par chunk** (quasi
linéaire, R² visuel excellent). Un chunk ≈ 0,44 M de q ≈ 7,9 M relations.

### 14.3 Le « +5,9 % » était un artefact de début de plage

À 52 min de crible, la moyenne était de 26 420 rel/s, soit +5,9 % sur les
24 973 rel/s de référence à `lim 100M/150M`. **Ce chiffre ne tient pas.** La
moyenne cumulée du run complet est de :

```
269 873 541 / 12 160 s  =  22 194 rel/s
```

soit **−11 % sous la référence `100M/150M`**. Le grand `lim` achète du débit en
début de plage (pic 27 658) puis le rend : la décroissance y est bien plus raide
qu'à `100/150` (−25 % du pic au chunk 34, sur ~13 M de q). C'est exactement le
piège identifié au §6, et il a été remarché deux fois de suite — d'abord par moi
en annonçant « +5,9 % », ensuite par les deux estimations concurrentes qui en
ont déduit un total de ~20 600 s.

**Conséquence directe** : `lim 200M/450M` n'est pas un levier de débit à c175. Il
déplace le travail, il ne le réduit pas.

### 14.4 La borne qui tranche

Le validateur tue à 14 400 s. Pré-crible 574 s ⇒ **13 826 s de crible** utiles.
En appliquant la pente mesurée à partir du point réel (269,9 M à 12 160 s) :

```
relations produites à 14 400 s   ≈  304 M
croisement requis (lpb 32/33)    =   441 M   (plancher c169 ; c175 ≥)
rapport                          =   68,9 %
déficit en relations             =   1,45×
```

**Le budget expire à 69 % du besoin en relations**, avant filtrage et algèbre
linéaire. Ce n'est plus une extrapolation sur deux hypothèses : c'est un point de
mesure (12 160 s de production réelle) et une pente mesurée sur 11 chunks.

Total projeté, deux hypothèses encadrantes :

| hypothèse | crible | + 574 s pré-crible | + ~2 200 s LA | total | écart |
|---|---|---|---|---|---|
| décroissance continue (−133/chunk) | 21 170 s | | | **23 942 s** | **+66 %** |
| débit gelé à 20 591 rel/s (favorable) | 20 470 s | | | **23 244 s** | **+61 %** |

La borne favorable ne dépend ni de la pente ni de la taille de la LA : même avec
un crible à débit constant et une algèbre linéaire gratuite, il resterait
20 470 + 574 = 21 044 s de crible, soit **+46 %**. Le verdict est robuste à toutes
les hypothèses contestables.

### 14.5 État mémoire en fin de run

Relevé au chunk 34 (12 160 s), utile pour une reprise éventuelle :

| ressource | valeur |
|---|---|
| `memfd pool` | **15 755 MB**, croissance ~380 Mo/chunk |
| `/tmp` | 4 419 MB (max 4 458) — **stable depuis le chunk 2** |
| `cgroup mem` | 0 MB (non instrumenté dans ce conteneur) |
| RSS `las` (co-crible CPU) | 5 113 MB, 500–508 rel/s |

Extrapolation à 441 M (chunk ~57) : `memfd` ≈ 24 Go, sous les 85 Go alloués.
Aucun mode de défaillance mémoire n'était proche — le run aurait pu aller au bout,
il a été arrêté pour raison économique, pas technique.

### 14.6 Ce que ce run ferme, et ce qu'il ne ferme pas

**Ferme** : la chaîne actuelle (GLAS, un seul GPU, 14 400 s) sur le 580, aux deux
profils connus du 560 — `100M/150M` (~20 800 s par arithmétique) et `200M/450M`
(**23 244–23 942 s mesurés**). Les deux dépassent le budget de 45 à 66 %.

**Ne ferme pas** : les approches qui ne sont pas cette chaîne. Un cribleur GPU
capable de 3LP diviserait le besoin en relations par ~2,5 et remettrait le 580
sous le budget — mais c'est un autre binaire, pas un réglage, et rien dans ces
mesures ne justifie l'investissement (le déficit à combler reste ~1,5×, et le
risque d'échec est total).

### 14.7 Trois enseignements méthodologiques

1. **Un débit mesuré sur 15 min n'est pas un débit de run.** Les 26 420 rel/s du
   début de plage et les 24 973 rel/s du §18.4 sont deux instantanés ; la seule
   grandeur qui vaut pour un chiffrage est la moyenne cumulée sur la durée du run.
2. **Une décroissance de −6 %/10 M peut en cacher une de −25 %/13 M.** La pente
   dépend du régime de `lim`, donc toute extrapolation de pente d'un profil à
   l'autre est invalide.
3. **Le seul chiffre qui tranche est celui qu'on mesure au point d'arrêt.** Ici :
   269,9 M à 12 160 s, quand le budget n'en permet que ~304 M pour un besoin de
   441 M. Un run interrompu au bon moment vaut mieux qu'un run mené au bout pour
   un chiffre qui ne peut pas changer la conclusion.

> **Note d'exécution** : ajouter des clés à `ENV_EXACT` dans `modal_rsa580.py` a
> suffi à invalider le cache d'image (le runner émet un `ENV` par surcharge), donc
> ~40 min de recompilation CADO. À corriger avant tout run futur.**

---

<a id="phase-11"></a>
## 15. Phase 11 — Les solutions des paliers précédents rouvrent le dossier (02/11)

### 15.1 Ce qui a été fait

Les six zips « Download Solution » (440 → 530) ont été extraits et comparés.
Le détail est dans **`SOLUTIONS_DIFF.md`**. Résumé de la chronologie :

- **≤ 440** : pas de GNFS (trial division + rho + yafu SIQS).
- **460 → 512** : cribleur maison `gpu_loop`, dont le source passe de 43 Ko à
  222 Ko et le coût de 17 à **5,0 ms/lattice**.
- **530** : **`gpu_loop` est abandonné** au profit de `cuda-sieve`, un projet
  **public CC0**. Run complet en **14 368,7 s** — 31 s de marge.
- **560** : chaîne entièrement différente — **Cognition GLAS + 15 patches**,
  485 M de relations brutes, 14 774 s en blind GCP. C'est la chaîne que ce dépôt
  utilise pour le 580 (voir §15.6).

### 15.2 Pourquoi c'est un problème pour le §13 et le §14

Le dossier a été clos deux fois sur la même phrase, écrite au §13.7 puis répétée
au §14.6 :

> « un cribleur GPU capable de 3LP […] c'est un autre binaire, pas un patch.
> Rien de tel n'est disponible ici. »

C'était vrai pour GLAS, et faux tout court. `cuda-sieve` gère **trois grands
premiers par côté** (`lpb ≤ 64`), choisit **rho pour un côté 2LP et ECM pour un
côté 3LP automatiquement**, cofactorise sur GPU, et tourne sur `sm_120`. Ses
binaires `bench`, `cofac_cpu`, `fbgen_gpu` sont **dans le zip du 530**, liés
statiquement au runtime CUDA (seule dépendance : `libcuda.so.1`).

### 15.3 Ce qui reste vrai, et ce qui tombe

**Reste vrai** : la chaîne GLAS 2LP est condamnée. Le §14 l'a mesuré —
269,9 M relations à 12 160 s, 304 M disponibles pour 441 M requis. Aucun
réglage ne comble 1,45×.

**Tombe** : « le 580 est hors de portée, point ». Ce qui est mesuré, c'est
qu'**une** chaîne ne suffit pas. La chaîne qui pourrait suffire — `cuda-sieve` en
3LP — n'a jamais été lancée ici. Le §14.6 disait « rien ne justifie
l'investissement » : c'était fondé sur un coût de plusieurs semaines. Le coût réel
d'un premier test est de quelques minutes.

### 15.4 L'arithmétique du saut

| | c160 (530 bits) | c175 (580 bits) |
|---|---|---|
| relations nécessaires | 160 M (sonde mesurée) | 441 M en 2LP / **199 M en 3LP** |
| coût par q | 24,1 ms/q | inconnu |
| temps total | 14 368,7 s | inconnu |

Le besoin est multiplié par 2,76× pour 50 bits, alors que le 530 n'avait que 31 s
de marge. **En 2LP, c'est perdu d'avance** — c'est notre §14. La 3LP divise le
besoin par ~2,2 : `199 M / 22 000 rel/s ≈ 9 000 s`. Tout dépend de deux nombres
inconnus à c175 en 3LP : **relations par q** et **ms par q**.

### 15.5 Le prochain jalon

Lancer `bench` sur notre polynôme c175 en mode 3LP, sur une bande courte, et lire
`ms/q`, `rel/q` et le taux de rejet ECM. Coût < 1 $, quelques minutes.

| résultat | conséquence |
|---|---|
| ≥ 22 000 rel/s | 199 M tient en ~9 000 s → le 580 redevient jouable |
| 12 000–22 000 rel/s | marginal, il faut rogner ailleurs |
| < 12 000 rel/s | dossier réellement clos, avec le bon outil mesuré |

### 15.6 Correction : le 560 était déjà là, et il utilise GLAS

Le §15.1 annonçait « 560 absent du lot ». **Faux** : il est dans le dépôt depuis
le 28/10 sous `rsa560_solver/`. Je l'avais pris pour notre propre archive parce
que son zip traîne à la racine et que le nom du dossier avait été simplifié.
Son `NOTICE` l'identifie sans ambiguïté : copyright « enigma-rsa contributors »,
code maison sous MIT, **Cognition GLAS** comme cribleur.

Ce que ça change :

| voie | cribleur | statut |
|---|---|---|
| A — rester sur GLAS 2LP | GLAS + 15 patches | **mesuré insuffisant** (§14 : +61 à +66 %) |
| B — passer en 3LP sur GPU | `cuda-sieve` | **jamais mesuré à c175** |

Le 560 a été gagné **en 2LP avec GLAS** — la 3LP n'était pas nécessaire de 530 à
560. Elle ne devient nécessaire que si c169 → c175 sort du budget, ce que le §14
indique. Les deux derniers paliers ont donc été gagnés par **deux équipes
différentes avec deux cribleurs différents** (530 : `cuda-sieve` ; 560 : GLAS),
ce qui explique pourquoi aucune ne publie la recette du 580 : chacune est au bout
de sa propre chaîne.

Ce que ça ne change pas : `cuda-sieve` reste le seul outil disponible capable de
3LP à c175, et c'est toujours la seule voie B. Mais il n'est **prouvé à aucun
palier au-delà de c160**, et c'est précisément ce que le probe doit établir.




