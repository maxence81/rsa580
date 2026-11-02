# Relais - Solveur RSA-580 / Enigma Subnet 63

## Contexte de la mission

Le projet vise à préparer une soumission pour le challenge **Breaking RSA** de
l'Enigma Subnet 63, opérée par qBitTensor Labs sur Bittensor. Le challenge
génère un semi-premier équilibré `N = p × q`; le solveur doit retrouver les
deux facteurs premiers et produire une sortie conforme au validateur Enigma.

Le palier ciblé est RSA-580 : `N` fait 580 bits, `p` et `q` environ 290 bits,
soit environ 175 chiffres décimaux. CADO-NFS classe ce palier comme `c175`.
La contrainte principale est une exécution complète en moins de **14 400 s**
(4 heures). Le solveur doit donc combiner :

1. recherche de polynôme GNFS ;
2. factor base ;
3. crible de relations GPU GLAS et co-crible CPU ;
4. déduplication, purge et construction de matrice ;
5. algèbre linéaire GPU/block Lanczos ;
6. calcul de racine carrée CADO-NFS et vérification de `p × q = N`.

Le travail local sert uniquement à construire et empaqueter l'image. Les
exécutions de factorisation doivent être faites sur une instance GPU distante
Modal, jamais sur le poste Windows.

## Dépôts et références

### Dépôt principal Enigma

- Dépôt officiel : [qbittensor-labs/enigma](https://github.com/qbittensor-labs/enigma)
- Fork local : [maxence81/enigma](https://github.com/maxence81/enigma)
- Workbench local : `C:\Users\maxen\enigma`
- Documentation Workbench :
  [workbench/README.md](https://github.com/qbittensor-labs/enigma/blob/main/workbench/README.md)
- Documentation Breaking RSA :
  [Breaking RSA README](https://github.com/qbittensor-labs/enigma/blob/main/workbench/challenges/breaking_rsa/README.md)
- Implémentation du challenge :
  [breaking_rsa.py](https://github.com/qbittensor-labs/enigma/blob/main/qbittensor/challenges/breaking_rsa.py)
- Runner Docker du Workbench :
  [docker_runner.py](https://github.com/qbittensor-labs/enigma/blob/main/workbench/runner/docker_runner.py)

Le dépôt local contient aussi le validateur et le contrat de sortie. Il est
actuellement dirty avec des modifications sans rapport dans plusieurs fichiers
quantum/HQP ; ne pas les réinitialiser ni les inclure dans la soumission RSA.

### Historique des solutions

- Solutions gagnantes :
  [qbittensor-labs/breaking-rsa-solutions](https://github.com/qbittensor-labs/breaking-rsa-solutions)

Ce dépôt sert de référence pour les paramètres, les profils de difficulté et
les améliorations historiques, mais le solveur courant est dans le dossier
local `rsa580_solver`.

### CADO-NFS et GLAS

- CADO-NFS Cognition :
  [cognition-research/cado-nfs-public](https://github.com/cognition-research/cado-nfs-public)
- Arbre CADO vendored dans le solveur :
  `third_party/cado-nfs-public`
- Commit CADO utilisé :
  `b5ca9c4fd3e331edc8978f93830f8de1e8dda70c`
- Le dépôt de travail du solveur indique le commit :
  `c00616b84c077199d8133fd8c07e97b072d17d3e`, branche `s5 / c175-580`.

Le Dockerfile compile CADO-NFS, `glas-gpu`, `gps1`, les filtres CADO, le
block-Lanczos GPU et les bibliothèques auxiliaires. Le contexte de build est
vendored afin que la construction de l'image ne dépende pas d'un clone réseau
du code source.

## Environnement du validateur

- Image : `linux/amd64`
- Utilisateur : non-root `miner`
- GPU : NVIDIA RTX PRO 6000, 96 Go VRAM, Ada Lovelace, CUDA `sm_120`
- CPU : 24 vCPU
- RAM : 85 Go
- Réseau à l'exécution : `--network none`
- Racine : `--read-only`
- Scratch : `/tmp` tmpfs `rw,noexec,nosuid,size=10g`
- Entrée : `/challenge_input/challenge_input.json` ou deux arguments CLI
- Sortie : stdout uniquement

La sortie stdout doit contenir les logs, puis le séparateur
`SOLUTION_OUTPUT_SEPARATOR`, puis un zip encodé en base64 contenant au minimum
`result.json` (`status`, `p`, `q`) et `solve_info.json`.

## Objectif

Factoriser un semi-premier RSA de 580 bits (`c175`, environ 175 chiffres) dans
la limite du validateur de 14 400 secondes, sur une machine Linux/amd64 avec
un GPU NVIDIA RTX PRO 6000 96 Go, 24 vCPU et 85 Go de RAM.

## État actuel

- Le test RSA-300 a réussi sur Modal en **398,5 s**.
- Le run RSA-580 a été lancé sur Modal avec le profil `lol810-maxou`, puis
  arrêté volontairement le 31/10/2026.
- App Modal du run RSA-580 :
  `ap-tFRss3VKGISdd7uu4fGoNK`
- L’app est confirmée `stopped`, avec 0 tâche active.
- Aucun facteur RSA-580 n’a été obtenu.
- Aucun `rsa580_submission.zip` n’a encore été généré.
- Les profils Modal `maxence-dabrowski81` et `maxence7567` étaient en état
  `paused`; `maxence81` avait dépassé sa limite de dépenses.

## Résultats du run RSA-580

Configuration observée :

- GNFS/CADO profil c175
- LPB : `32/34`
- MFB : `64/68`
- RLIM : `250000000`
- ALIM : `600000000`
- Première sonde : `473000000` relations brutes
- GPU : GLAS avec session CUDA persistante
- Co-crible CPU LAS activé

Performance :

- Pic initial : environ `49 000 rel/s`
- Débit en fin de crible GPU : environ `32 500 rel/s`
- Relations atteintes avant arrêt : `517360467`
- `/tmp` : environ `6,9 Go`, sous la limite tmpfs de 10 Go
- Mémoire : aucun dépassement signalé

La première sonde à `476890759` relations a donné :

```text
SHORT
unique=345637771
sing_excess=-18076826
sing_ncols=29566131
```

La seconde sonde à `488764412` relations a donné :

```text
SHORT
unique=353111364
sing_excess=-17845796
sing_ncols=30284709
```

Le crossover estimé était `528764412` relations. Le run a été arrêté à
`517360467` relations, avec moins de 12 minutes restantes avant la limite.

## Fichiers importants

- Solveur : [rsa580_solver](C:/Users/maxen/enigma_rsa/rsa580_solver)
- Dockerfile : [Dockerfile](./Dockerfile)
- Runner Modal : [modal_rsa580.py](../modal_rsa580.py)
- Informations de soumission : [SUBMISSION_INFO.txt](./SUBMISSION_INFO.txt)
- Workbench Enigma : `C:\Users\maxen\enigma`

## Runner Modal

Le runner construit l’image depuis le Dockerfile du solveur et exécute le
solveur uniquement sur une instance Modal GPU. Le Dockerfile original n’est
pas modifié par le runner.

Commande de lancement :

```powershell
$env:PYTHONIOENCODING="utf-8"
$env:PYTHONUTF8="1"
modal profile activate lol810-maxou
Set-Location C:\Users\maxen\enigma_rsa
modal run --detach .\modal_rsa580.py --difficulty 580
```

Vérifier l’état :

```powershell
modal profile activate lol810-maxou
modal app list
modal app logs ap-<APP_ID> --tail 100 --timestamps
```

Arrêter explicitement :

```powershell
modal app stop -y ap-<APP_ID>
```

Le générateur local du challenge nécessite `gmpy2` dans le Python utilisé par
la CLI Modal. Il a été installé dans :

```text
C:\Users\maxen\AppData\Local\Programs\Python\Python310
```

## Prochaines étapes recommandées

1. Ne pas relancer immédiatement un RSA-580 avec les mêmes paramètres : le
   run a montré que le crossover arrive trop tard pour laisser une marge
   suffisante à l’algèbre linéaire.
2. Examiner `stop_cost.py`, les règles `STOP_SHAPE` et le comportement des
   sondes pour réduire le nombre de relations nécessaires.
3. Vérifier si le co-crible LAS consomme une partie excessive du temps ou du
   scratchpad ; il a produit des relations à environ 700-800 rel/s.
4. Tester toute modification sur RSA-500 ou RSA-560 avant de consommer un
   nouveau run GPU RSA-580.
5. Si un run RSA-580 réussit, conserver les logs et décoder la sortie
   `ENIGMA-SOLUTION-OUTPUT-BEGIN/END`.
6. Générer l’archive de soumission en excluant les fichiers Python compilés :

```powershell
Set-Location C:\Users\maxen\enigma_rsa\rsa580_solver
Compress-Archive -Path * -DestinationPath ..\rsa580_submission.zip
```

Pour une archive strictement conforme aux exclusions `*.pyc` et
`__pycache__`, utiliser `zip` dans un environnement Linux/WSL :

```bash
zip -r ../rsa580_submission.zip . -x '*.pyc' -x '*__pycache__*'
```

## Avertissements

- Ne pas exécuter la factorisation localement : utiliser Modal GPU uniquement.
- Le validateur utilise `--network none`, `--read-only`, un tmpfs `/tmp` de
  10 Go, 85 Go de RAM, 24 CPU et l’utilisateur non-root `miner`.
- Toute modification du Dockerfile doit préserver le contrat stdout :
  logs, séparateur `SOLUTION_OUTPUT_SEPARATOR`, puis zip base64.
- Le run précédent n’a pas prouvé que RSA-580 est faisable sous 4 heures ; il
  a seulement validé la compilation distante, le protocole et le débit de
  crible.

## Verrou identifié : les caps de buffers GLAS (2026-11-01)

Le run RSA-580 n'a pas échoué sur le crossover, il était structurellement
hors budget. La chaîne :

1. `factor_c175.sh:132-135` fixe le régime de production à **2 large primes**
   parce que le défaut 3LP (`30/31, mfb 60/90`) *« overflows glas's GPU
   buffers (ledger bake-off 4) »*.
2. Le 2LP force un `lim` élevé pour garder du rendement : `250M/600M`.
3. Base de facteurs = π(250M) + π(600M) = **45,0 M de colonnes**. La matrice ne
   peut pas être plus petite que sa base : `N ≥ 30 M` (30,28 M de colonnes
   observées à 488 M de relations, soit 67 % de la base déjà remplies).
4. `LA = 12,7 s/(M)²` → **11 400 s à 18 500 s** d'algèbre linéaire seule, pour
   une fenêtre de 14 400 s.

Règle de conception qui en découle : **π(lim0) + π(lim1) ≤ 18 M** pour que
`LA ≤ 3 000 s` (N ≤ 15,4 M). `250/600` la viole d'un facteur 2,5 ; `100/150`
(profil 560) la respecte (14,2 M → N ≈ 12 M → LA ≈ 1 850 s).

### Correctif appliqué

`vendor/glas-caps-env.patch` existait dans l'arbre mais **n'était jamais
appliqué par le Dockerfile** : l'image embarquait les caps codés en dur
(margin 1.25, `max_survivors = chunk/64`, `max_hits = chunk/8`), dimensionnés
pour 2 LP. D'où l'overflow 3LP, et donc le 2LP, et donc `lim 250M/600M`.

- Ajout de `gpu/glas_caps_patch.py` (patch idempotent par remplacement de
  chaînes, échoue si la source a dérivé ; validé sur
  `third_party/cado-nfs-public/gpu-siever/src/sieve_core_gpu.cu`).
- Câblé dans le `Dockerfile` (COPY + chaîne de patches + marqueurs
  `GLAS_BUCKET_MARGIN`, `GLAS_SURV_DIV` vérifiés dans la source *et* dans le
  binaire). Défauts inchangés : sans variable d'environnement, le comportement
  est bit-à-bit celui d'avant.

Nouveaux réglages, lus une fois à l'init de glas :

| Variable | Défaut | Rôle |
|---|---|---|
| `GLAS_BUCKET_MARGIN` | 1.25 | marge sur la densité de hits (3LP λ≈2.8 → 2.5-3.0) |
| `GLAS_SURV_DIV` | 64 | `max_survivors = chunk/div` (3LP → 16 ou 8) |
| `GLAS_HITS_DIV` | 8 | `max_hits = chunk/div` (→ 4 ou 2) |
| `GLAS_FCAND_MAX` | `FCAND_MAX` | capacité candidats, à monter avec `SURV_DIV` |

Le coût est de la VRAM (par slot), pas du temps. Un overflow résiduel retombe
toujours sur le fallback CPU par q — correct mais lent — donc ce patch ne peut
pas changer un facteur.

### Test à faire (avant tout run 580)

1. Rebuild de l'image, vérifier que le build passe les marqueurs.
2. Smoke test 10 min sur un N 580, régime 3LP **autorisé par le pipeline**
   (`LPB1 ∈ {32,33,34}`) : `RSA580_LPB1=32 RSA580_MFB1=99
   RSA580_LIM…=100M/130M RSA580_LAMBDA1=2.8` avec
   `GLAS_BUCKET_MARGIN=3 GLAS_SURV_DIV=16 GLAS_HITS_DIV=4`.
3. Lire les lignes `# GPU overflow at q=… (caps surv=… hits=…)` : leur absence
   = 3LP tient sur le GPU. Mesurer le rel/s et le nombre de survivants.
4. Décider sur le temps total (`crible + filtre + LA`), jamais sur le rel/s
   seul : c'est l'erreur qui a coûté le run du 31/10.

### Résultats des tests du 2026-11-01 (négatifs, à ne pas refaire)

Build : OK. `glas_caps_patch` s'applique dans la vraie chaîne, les marqueurs
passent, `nvcc -arch=sm_120` compile, `glas-gpu zmm/kmask insns: 0`. Le patch
est donc en place et inoffensif par défaut.

Deux runs lancés sur Modal (profil `lol810-maxou`), même N (`--seed 12345`),
régime 3LP `lpb 32/32 mfb 64/99 lim 100M/130M lambda 2.0352/2.8` :

| Run | Caps / session | Crible observé |
|---|---|---|
| `ap-HgwQGUp0iUkzmHlXYnb5Fw` | margin 3, surv 16, hits 4, session ON | **0 relation GPU en ~20 min** ; co-crible CPU 358 rel/s ; 1 chunk CPU puis plus rien |
| `ap-O89QHSsTFO6lgmVTVMYJwp` | margin 2, surv 32, hits 4, session OFF, PS 60 s | **0 relation GPU en ~8 min** ; co-crible CPU 347 rel/s |

Référence 2LP du run du 31/10 : ~41 000 rel/s GPU.

Conclusion : **les caps n'étaient que le symptôme.** Le coût du 3LP est dans le
filtre à survivants (ECM sur des cofacteurs jusqu'à ~2^75), pas dans les
capacités mémoire : ~100× plus lent que le 2LP. Lever les caps ne rend pas le
3LP exploitable sur GLAS. Le 3LP est donc une impasse *logicielle*, pas un
réglage à trouver.

Conséquence pour le 580 : on reste en 2LP, donc `lim` est borné par la règle
π(lim0)+π(lim1) ≤ 18 M. Le budget se joue alors entièrement sur le débit de
crible (il faut ~550-600 M de relations à ≥30 k rel/s), pas sur l'algèbre
linéaire.

Piste annexe relevée pendant les tests : le polyselect du run 1 s'est arrêté à
**MurphyE 7,73e-11** après 572 s, alors que son propre seuil `PS_ADAPT`
(1,15e-9) n'a jamais été atteint. Un facteur ~15 sous la cible interne : c'est
potentiellement 10-20 % de relations en moins, donc la piste la moins chère qui
reste.

## Mesures du 2026-11-01 (après-midi) — la vraie loi de coût

Quatre runs instrumentés (même N, seed 12345). Ce qui suit remplace la règle
« π(lim0)+π(lim1) ≤ 18 M » écrite plus haut : elle ne bornait que l'algèbre
linéaire et ignorait le nombre de relations, qui est le terme dominant.

### 1. Le « crossover » du prédicteur est un plafond, pas une estimation

`stop_cost.py` clampe son point de sonde prédit dans
`[PROBE_AT + PROBE_STEP/2, PROBE_AT + 4*PROBE_STEP]`. Quand le vrai crossover
est à plus de 4 pas, la valeur rapportée **est exactement le plafond** :

| run | `lim` | dernier raw | valeur annoncée | `last + 4*PROBE_STEP` |
|---|---|---|---|---|
| 2026-10-31 | 250/600 | 488 764 412 | 528 764 412 | 488 764 412 + 4×10 M ✓ |
| run A | 120/200 | 97 032 668 | 217 032 668 | 97 032 668 + 4×30 M ✓ |

C'est la même panne deux fois. **Ne jamais lire ce nombre comme un crossover.**
Le vrai crossover linéaire se calcule sur la pente d'excès mesurée :

- run A, sondes 2→3 : excès −14 167 470 → −14 004 227 sur +31,83 M raw
  → pente 5,13e-3/raw → **crossover ≈ 2,73 G raw (35,7 h)** à `lim 120/200`.

Donc `lim 120/200` est hors sujet, pas « limite ».

### 2. Loi de complétion : `raw_complet ≈ 29 × FB`

Le critère n'est pas l'excès mais `nrows ≥ ncols`. Le point de production c169
(560 bits) le donne directement : `lim 100/150` → FB 14,20 M, **420 M raw**,
soit **r = 29,6**. Vérification croisée sur le run A (`lim 120/200`, FB
17,92 M) : à 97,0 M raw, `nrows/FB = 0,0555` ; la loi de puissance
`nrows/FB ∝ r^1,75` redonne 1,07 à r = 29 → cohérent.

Conséquence : le nombre de relations à produire est **proportionnel au FB**, et
le temps de crible l'est donc aussi. Réduire `lim` n'est pas gratuit en crible,
seulement en LA.

### 3. Débit mesuré

| run | `lim` | FB | débit (chunks 1-2) | MurphyE |
|---|---|---|---|---|
| c169 (560 b) | 100/150 | 14,20 M | 27 632 rel/s | — |
| run A | 120/200 | 17,92 M | 24 141 → 22 400 | 1,55e-10 |
| run B | 80/120 | 11,51 M | 21 012 → 20 996 | 5,92e-11 |
| run C | 40/60 | 5,99 M | **< 4 160** (bloqué) | 1,27e-11 |

Le débit est **très peu sensible au `lim`** (exposant ~0,3 sur 11,5→17,9 M) :
le crible est limité par le débit GPU, pas par la douceur. Corollaire : le temps
de crible total `29·FB / débit(FB)` décroît lentement avec FB, alors que la LA
croît en FB². L'optimum est donc à FB **petit**, pas grand.

### 4. La vraie contrainte : le FB, pas l'appariement `lim`/`lpb`

Le run C (`lim 40/60` avec `lpb 32/33`) ne produit **aucun chunk en 16 min**.
J'ai d'abord supposé un désaccord `lim`/`lpb` (écart de 6,75 bits, relations
dominées par des colonnes de grands premiers que le crible singleton élimine).
**C'est faux, et le test le montre** : le run H, en `lpb 30/31` (écart ramené à
4,5 bits, la recette CADO pour c175) avec `lim 48/67`, donne **4 667 rel/s** —
identique aux 4 658 rel/s du run I en `lpb 32/33` au même `lim`. Apparier `lpb`
à `lim` ne change rien.

La cause est donc simplement la **taille du FB** : `débit ∝ FB^1,58`. Un petit FB
est lent *par relation*, et c'est tout. La recette CADO `lpb 30/31, lim 48/67`
n'est pas meilleure ici, elle est juste plus petite.


### 5. Modèle de coût et point de fonctionnement

`total ≈ 530 (polyselect+makefb) + 29·FB/débit(FB) + 12,67·(1,05·FB)² + ~1 300`
où 12,67 = `STOP_KAPPA` 9,9 × `STOP_LA_SCALE` 1,28, et FB en millions.

Avec `lpb 30/31, lim 48/67` (FB 6,87 M, 199 M raw, LA 730 s) et un débit de
20-25 k rel/s, le total tombe vers **9 500-11 500 s** : c'est la première
configuration qui tient dans 14 400 s. À l'inverse `lim 120/200` demande
520 M raw → 23 200 s de crible seul, et `lim 250/600` 1,3 G raw.

### 6. Polyselect : saturé, pas sous-alimenté

`PS_ADAPT` à P = 1,85 M sature : 6 batchs font passer MurphyE de 5,775e-11 à
5,917e-11 (**+2,5 % pour 187 s**), et 20 batchs n'ont rien changé de visible.
Augmenter P à 6 M ralentit chaque batch de 70 s à 254 s pour le **même** nombre
de candidats (~2 300) : c'est l'`ad` qui borne, pas P. Le seuil interne
1,15e-9 n'est pas atteignable dans le budget — il est probablement calé pour
c160, pas pour c175. Conclusion : **ne pas investir plus de ~600 s dans le
polyselect**, et ne pas compter sur MurphyE comme levier.

### 7. Outillage ajouté

- `POLY_ONLY=/dev/stdout` fait cracher le polynôme complet dans les logs
  (le pipeline ne loguait que `c5`/`skew`) : c'est le seul moyen de le récupérer,
  il n'y a pas de volume Modal.
- `POLY_B64` (dans `modal_rsa580.py`) réinjecte ce polynôme en `POLY_IN` :
  indispensable pour comparer deux régimes **à polynôme fixe**, car MurphyE
  varie d'un facteur ~5 d'un tirage à l'autre et noierait la comparaison.
- `GLAS_BUCKET_MARGIN` / `GLAS_SURV_DIV` / `GLAS_FCAND_MAX` (via
  `gpu/glas_caps_patch.py`) rendent les caps GLAS réglables.

### 8. Piège d'exploitation Modal

`modal run --detach` ne survit pas au SIGTERM du client : trois apps (dont deux
runs complets) ont été tuées en fin d'appel shell. **Toujours lancer en tâche de
fond** (`run_in_background`), sinon l'app démarre puis est annulée.

### 9. Modèle de coût complet et verdict de faisabilité

Mesures propres, toutes sur la même tranche de q `[2,2 M ; 2,4 M)` :

| run | `lim` | FB | polynôme | débit |
|---|---|---|---|---|
| J | 120/200 | 17,92 M | F (60 s) | 21 206 rel/s |
| I | 48/67 | 6,87 M | **F (identique)** | 4 658 rel/s |
| K | 120/200 | 17,92 M | F + `ncurves 8` | 20 681 rel/s |
| D | 120/200 | 17,92 M | MurphyE 1,71e-10 | **33 966 rel/s** |

Trois lois en sortent :

1. **`débit ∝ FB^1,58`** (J vs I, polynôme identique — le seul couple non
   confondu). Le rendement par q croît donc comme FB² (il faut que *les deux*
   côtés soient friables) alors que le travail par q croît comme FB.
2. **`ncurves` n'est pas un levier** : 8 au lieu de 17 ne donne rien (−2,5 %,
   dans le bruit). GLAS est limité par le crible GPU, pas par le filtre ECM.
   Corollaire : le 3LP restera une impasse.
3. **Le polynôme vaut ~1,6×** : D (1,71e-10) fait 33 966 contre 21 206 pour J au
   même `lim`. C'est le plus gros levier unitaire disponible.

Coût total, avec `raw = 29·FB`, `LA = 12,67·(1,05·FB)²` et ~1 300 s de fixe :

| FB | `lim` | brut | crible | LA | **total** |
|---|---|---|---|---|---|
| 6,87 M | 48/67 | 199 M | 27 071 | 659 | 29 030 |
| 10,0 M | 70/100 | 290 M | 21 767 | 1 397 | 24 464 |
| 14,0 M | 100/150 | 406 M | 17 902 | 2 738 | 21 940 |
| **17,92 M** | **120/200** | **520 M** | **15 511** | **4 486** | **21 296** |
| 22,0 M | 150/250 | 638 M | 13 768 | 6 761 | 21 829 |
| 30,0 M | 200/350 | 870 M | 11 498 | 12 572 | 25 370 |
| 45,0 M | 250/600 | 1 305 M | 9 085 | 28 287 | 38 672 |

Le minimum est **~21 300 s à `lim 120/200`** (FB 17,9 M), soit **1,48× le budget
de 14 400 s**. Le run 250/600 du 31/10 était donc à 2,7× du budget, pas à 1,05×
comme le laissait croire le crossover clampé.

**Ce qu'il faudrait pour tenir en 14 400 s** : environ **+50 % de rendement**.
Les seules voies identifiées, par ordre de plausibilité :

- un polynôme à MurphyE ≥ 2,5e-10 (le run P, 40 batchs, teste exactement ça) :
  à +30 % de débit il reste ~16 000 s, encore court ;
- un `r` réel plus faible que 29. C'est l'inconnue qui décide : D atteindra
  `r ≈ 24` avant son timeout. **Si le vrai `r` est ≤ 24, D passe ; s'il est 29,
  il manque 20 %.** Les sondes de D à 150 M et 180 M tranchent.
- augmenter FB au-delà de 18 M ne paie pas : la LA en FB² mange tout.

Verdict provisoire : le 580 est **à la limite**, pas hors de portée — mais le
couple (polynôme, `r`) décide, pas le réglage du `lim`.

### 10. Correction du modèle et écart final

`STOP_LA_SCALE` vaut **1** par défaut (le 1,28 supposé était une erreur de
lecture) : `kappa = 9,9`, donc `LA = 9,9·(1,05·FB)²`. Le tableau corrigé :

| FB | `lim` | brut | crible | LA | **total** |
|---|---|---|---|---|---|
| 14,0 M | 100/150 | 406 M | 17 660 | 2 139 | 21 099 |
| 16,0 M | 115/190 | 464 M | 16 341 | 2 794 | 20 436 |
| **17,92 M** | **120/200** | **520 M** | **15 300** | **3 505** | **20 105** |
| 20,0 M | 135/230 | 580 M | 14 354 | 4 366 | **20 020** |
| 22,0 M | 150/250 | 638 M | 13 581 | 5 283 | 20 164 |

Minimum **~20 000 s** à `lim 135/230`. Pour tenir dans 14 400 s il faudrait
`crible + LA ≤ 13 100 s`, ce qui demanderait **52 500 rel/s** au point
`lim 120/200` — soit **1,55×** le débit mesuré de D (33 966).

Le débit n'est pas limité par le filtre (`ncurves` 8 = aucun gain) ni par un cap
tronqué (lever `GLAS_SURV_DIV` à 32 ne fait que ralentir ; à 16 + `FCAND_MAX`
4 M, OOM CUDA franc). Il est limité par le crible GPU lui-même.

**Le seul levier restant est le polynôme.** D (MurphyE 1,71e-10) fait 33 966
rel/s là où le polynôme de F (60 s de polyselect) en fait 21 206 au même `lim` :
**1,60×** pour un écart de MurphyE. Si un polynôme atteint 50 000 rel/s, le 580
tient (13 905 s). C'est exactement ce que le run P (40 batchs, `PS_ADAPT_MAXB`
40) cherche, et le run D (20 batchs) a montré que le temps de polyselect paie
réellement : 5,92e-11 à 6 batchs → **1,71e-10 à 20 batchs (×2,9)**.

### 11. Sur la croissance de `nrows` (piège d'extrapolation)

`nrows/FB` mesuré : 0,0224 à r = 1,78 (D) ; 0,0387 à r = 3,64 et 0,0555 à
r = 5,41 (run A). L'exposant local vaut 0,77-0,91 : une extrapolation en loi de
puissance depuis r < 6 donnerait `r ≈ 128`, ce qui **contredit** le point de
complétion c169 (r = 29,6). La raison est que la croissance n'est pas une loi de
puissance : c'est une percolation du 2-core, qui s'emballe au voisinage de la
densité critique. **Ne jamais extrapoler `nrows` depuis r < 6** ; le seul ancrage
fiable est le run c169 terminé, r = 29,6.

### 12. Verdict : le polyselect est épuisé, et le 580 coûte 1,17× le 560

Deux polyselects longs, deux tirages indépendants :

| run | batchs | candidats | temps | **MurphyE final** |
|---|---|---|---|---|
| D | 20 | 46 797 | 1 381 s | **1,710e-10** |
| P | 40 | 93 679 | 2 858 s | **1,642e-10** |

Doubler le nombre de batchs et de candidats ne donne **rien** (1,642 contre
1,710, soit 4 % *en moins*, dans le bruit). Le MurphyE plafonne à ~1,7e-10 pour
cette configuration de recherche, très loin du seuil interne `PS_ADAPT` de
1,15e-9, qui n'est pas calibré pour c175. **Le levier polynôme est donc épuisé :
ne plus y investir de temps.**

Conséquence : le débit plafonne à ~34 000 rel/s à `lim 120/200`, et le coût
total à ~20 000 s (tableau §10). Le run D, lancé en conditions réelles, atteint
~345 M raw avant son timeout, soit `r ≈ 19` là où il en faudrait ~30 : il manque
**~35 % de relations**, ce qui est cohérent avec le modèle.

**Mais l'écart au palier déjà résolu est faible.** Le point de production c169
(560 bits), d'après le commentaire de `factor_c169.sh` :

| | 560 (c169) | 580 (ce travail) | ratio |
|---|---|---|---|
| `lim` | 100/150 | 120/200 | |
| FB | 14,20 M | 17,92 M | 1,26× |
| brut | 420 M | ~538 M | 1,28× |
| débit | 27 632 rel/s | ~32 000 rel/s | 1,16× |
| crible | 15 200 s | ~16 800 s | 1,11× |
| LA | 2 139 s | 3 505 s | 1,64× |
| **total** | **17 339 s** | **~20 300 s** | **1,17×** |

Le 580 ne coûte que **17 % de plus** que le 560. Autrement dit : si le 560 tient
dans le budget, le 580 est à 17 % — et non à 2× comme le suggérait le crossover
clampé du 31/10.

**Incohérence à signaler** : le point c169 enregistré (15 200 s de crible +
2 139 s de LA = 17 339 s) dépasse déjà à lui seul la limite annoncée de
14 400 s. Donc soit la limite réelle est supérieure à 14 400 s, soit les chiffres
c169 du commentaire sont périmés (build plus lente). À vérifier avant de
conclure : c'est ce chiffre, et non le réglage du solveur, qui décide si le 580
est à portée.

Ce qu'il faudrait pour tenir en 14 400 s : **~53 000 rel/s** au point
`lim 120/200` (contre 34 000 mesurés), soit **1,56×** de débit en plus. Aucun
levier logiciel identifié ne donne ça : `ncurves` (rien), caps GLAS (OOM ou plus
lent), polynôme (épuisé), `lim` (optimum déjà atteint). Il faudrait un crible
plus rapide, ou ~40 % de temps en plus.

### 13. CORRECTION MAJEURE : l'optimum est au coude de la courbe de débit, et le 580 TIENT

Les §10 et §12 concluaient « infaisable » — **c'était faux**, et l'erreur venait
d'avoir mesuré le débit uniquement aux grands FB (120/200 et au-delà), où il
plafonne, en extrapolant vers le bas avec un exposant de loi de puissance. Le
débit n'est pas monotone en FB, il est **concave avec un coude vers F ≈ 10-12**.
Mesures à polynôme fixe (P, MurphyE 1,642e-10), même bande de q `[2,2 M ; 2,4 M)` :

| `lim` | FB | débit | brut (r=29) | crible | LA | **total** |
|---|---|---|---|---|---|---|
| 48/67 | 6,87 M | 4 658 | 199 M | — | — | (effondrement) |
| **70/100** | **10,0 M** | **26 380** | **290 M** | **10 993** | **1 091** | **13 385 s ✓** |
| 80/120 | 11,5 M | 28 226 | 334 M | 11 826 | 1 446 | 14 572 s (1 % trop) |
| 100/150 | 14,2 M | 29 614 | 412 M | 13 906 | 2 201 | 17 406 s |
| 120/200 | 17,92 M | 33 505 | 520 M | 15 511 | 3 505 | 20 316 s |
| 135/230 | 20,0 M | 32 130 | 580 M | 18 052 | 4 366 | 23 718 s |

Le débit ne varie que de 26 380 à 33 505 (+27 %) entre `lim 70/100` et
`120/200`, alors que le nombre de relations à produire, lui, est **proportionnel
au FB** (290 M → 520 M, +79 %). Donc **il faut prendre le plus petit FB possible
au-dessus du coude** : `lim 70/100` est le point de fonctionnement optimal, à
**13 385 s**, soit 7 % de marge sous la limite.

C'est aussi ce qui explique pourquoi le palier 560 avait choisi `lim 100/150` :
c'était le coude pour son N. Le 580 déplace le coude un peu plus haut en FB mais
la marge reste.

Marge de sûreté sur `r` (le seul paramètre non mesuré directement) : à
`lim 70/100` et 26 380 rel/s, le budget tient tant que **r ≤ 31**. Au-delà de
r = 32 le run dépasse. C'est le point à surveiller sur les sondes.

Deux tentatives tournent avec cette configuration, `lim 70/100` (S) et
`lim 80/120` (T), polynôme P injecté, budget complet.

### 14. Reprise du 2026-11-01 (soir) — panne Modal après upgrade, et contradiction débit/décroissance

#### 14.1 La panne « Could not connect to the Modal server » n'était pas une panne

Après l'upgrade du client Modal **1.4.3 → 1.6.3** (imposé par `lol810-maxou2`,
qui exige l'image builder `2026.10`), **toutes** les commandes sont tombées, y
compris `modal profile list` qui affichait les cinq profils en
`Unknown (profile misconfigured)`. Le message est trompeur : `~/.modal.toml`
était intact et se parsait correctement (`config._user_config` listait bien les
cinq sections). Le vrai diagnostic est dans la trace :

```
ImportError: A proxy is configured (http://127.0.0.1:50710) but the
'python-socks' package is not installed.
  -> ConnectionError("Could not connect to the Modal server.")
```

Le bac à sable exporte `HTTP_PROXY` / `HTTPS_PROXY` / `http_proxy` /
`https_proxy` = `http://127.0.0.1:50710`. **Modal 1.6.x honore ces variables
d'environnement, 1.4.3 les ignorait** ; et il refuse de passer par un proxy
SOCKS/HTTP sans `python-socks`. D'où l'échec total, déguisé en problème de
configuration de profil.

Correctif retenu (pas d'installation, pas de changement de config) : **retirer
les variables de proxy de l'environnement** au lancement.

```bash
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
    -u ALL_PROXY -u all_proxy \
    "C:/Users/maxen/AppData/Local/Programs/Python/Python310/python.exe" \
    -m modal run --detach ./modal_rsa580.py --difficulty 580 --seed 12345
```

Vérification : `modal token info` → `Workspace: lol810-maxou2`. À appliquer à
**toutes** les invocations `modal` désormais, sinon le message « profile
misconfigured » réapparaît.

#### 14.2 Deuxième blocage : Python 3.10 n'existe plus dans l'image builder 2026.10

Une fois la connexion rétablie, `probe_profile.py` a échoué autrement :

```
Python 3.10 is not supported by the '2026.10' Image builder.
Set `python_version` to one of: ['3.11', '3.12', '3.13', '3.14', '3.14t', '3.15', '3.15t']
```

L'image implicite d'une fonction sans `image=` est construite à partir du Python
local (3.10). Correctif : `image=modal.Image.debian_slim(python_version="3.11")`
sur la sonde. **`modal_rsa580.py` n'est pas concerné** : il utilise
`Image.from_dockerfile(...)`, donc la version de Python vient du Dockerfile.
Sonde validée : `PROBE_RESULT: ok`, coût ~0.

#### 14.3 État des lieux des workspaces (2026-11-01 soir)

| profil | état |
|---|---|
| `lol810-maxou2` | **OK** — token `ak-SBa3dA…`, `ac-NGUWl5JjRo7wt5BALbhZhS`, 0,00 $ aujourd'hui |
| `lol810-maxou` | 42,67 $ dépensés aujourd'hui, plafond atteint |
| `maxence81` | 0,00 $ mais plafond à 0 → refusé |
| `maxence7567`, `maxence-dabrowski81` | workspace en pause |

#### 14.4 Contradiction à trancher : la décroissance du débit est-elle durable ?

Le §13 chiffre `lim 70/100` à 13 385 s **en supposant le débit plat**. Or les
sondes courtes mesurent une décroissance de **3,18 % par 10 M de brut**. Les deux
ne peuvent pas être vrais simultanément, et l'écart est décisif :

| hypothèse | crible | LA | total | verdict |
|---|---|---|---|---|
| débit plat à 26 380 rel/s | 10 993 s | 1 091 s | **13 385 s** | tient (7 % de marge) |
| décroissance 3,18 %/10 M non bornée | 17 730 s | 1 091 s | **18 821 s** | dépasse de 31 % |

**L'argument en faveur du débit plat est solide** : le run c169 (560 bits) a
produit 420 M de relations en 15 200 s de crible, soit **27 632 rel/s en moyenne
sur 420 M** — exactement le même chiffre que son débit instantané. Sur 420 M de
relations, une décroissance de 3,18 %/10 M aurait divisé le débit par
`exp(0,0318 × 42) = 3,8`, ce qui est incompatible avec la mesure. La
décroissance observée sur les sondes courtes est donc **transitoire** (premier
intervalle, warm-up, absorption des relations faciles), pas structurelle.

Ce qui reste incertain est **où** le débit se stabilise, et c'est précisément ce
que la sonde à 200 M doit révéler. Pronostics :
- stabilisation à 25 000 rel/s → ~12 500 s de crible, **tient** ;
- stabilisation à 22 500 rel/s → ~13 600 s de crible, tient de justesse ;
- décroissance qui persiste → dépassement, il faudra descendre encore le FB.

Attention au coût non modélisé : le **filtrage** de ~290 M de relations sur
24 vCPU n'est pas dans les 13 385 s (le chiffre c169 de 17 339 s = 15 200 crible
+ 2 139 LA, filtrage exclu). Prévoir 1 500-2 500 s de plus.

#### 14.5 Paramètres du run relancé

`lim 70/100`, polynôme P injecté par `POLY_B64`, sonde à 200 M puis tous les
40 M — la première décision tombe après ~7 600 s de crible, ce qui laisse
~6 800 s pour finir les ~86 M restants et le downstream.

```bash
RSA580_CPU_LAS=0 LPB0=32 LPB1=33 MFB0=64 MFB1=66 \
RLIM=70000000 ALIM=100000000 LAMBDA0=2.0352 LAMBDA1=2.0379 \
FIRST_PROBE=200000000 PROBE_STEP=40000000 \
POLY_B64="$(cat /tmp/polyP_b64.txt)"
```

`LAMBDA1=2.0379` et non 2.08 : c'est la valeur que `factor_c175.sh` associe à
`LPB1=33` (2.08 est celle de `LPB1=34`, ligne 64-65).

Démarrage confirmé à 14:00:20 : polynôme P injecté (`skew 19723314.151
c5 1103760`), base de facteurs construite (85,5 Mo), crible GPU lancé à 14:00:22.

#### 14.6 Coût caché : un workspace neuf repaie la compilation de CADO

Le cache d'images est **par workspace**. Sur `lol810-maxou2`, vierge, le build a
pris **~40 minutes** (apt + compilation complète de CADO-NFS, jusqu'à 98 %+),
alors que les runs précédents sur `lol810-maxou` réutilisaient un cache chaud.
Ce n'est pas imputé au timeout de 14 400 s (le build est hors fonction), mais
c'est 40 min de latence à prévoir avant tout premier run sur un compte neuf.

Attention aussi : `.env(ENV_OVERRIDE)` fait partie de la définition d'image,
donc **chaque combinaison de variables d'environnement crée une image
distincte**. Les couches Dockerfile (la compilation, la partie chère) restent
en cache, seule la petite couche `.env` est reconstruite — mais si le cache est
froid, chaque nouveau jeu de paramètres repaie les 40 min.

### 15. VERDICT DÉFINITIF : le §13 est FAUX, le 580 ne tient pas dans 14 400 s

Le §13 annonçait « 13 385 s, le 580 TIENT ». **C'est réfuté par la mesure.**
Cette section remplace le §13 ; ne pas s'y fier.

#### 15.1 La limite de 14 400 s est confirmée, et elle est dure

Interrogation directe de l'API publique des challenges (aucune authentification) :

```
GET https://challenges.qbittensorlabs.com/v1/challenges/a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d
```

| milestone | bits | `max_solution_runtime` | statut | prix | soumissions |
|---|---|---|---|---|---|
| 340-bit RSA | 340 | 14 400 | Complete | 10 000 $ | 4 |
| 460-bit RSA | 460 | 14 400 | Complete | 10 000 $ | 59 |
| 480-bit RSA | 480 | 14 400 | Complete | 10 000 $ | 33 |
| 500-bit RSA | 500 | 14 400 | Complete | 20 000 $ | 47 |
| 512-bit RSA | 512 | 14 400 | Complete | 20 000 $ | 5 |
| 530-bit RSA | 530 | 14 400 | Complete | 10 000 $ | 1 |
| 560-bit RSA | 560 | 14 400 | Complete | 20 000 $ | 30 |
| **580-bit RSA** | **580** | **14 400** | **Incomplete** | **10 000 $** | **0** |

Donc : la valeur est **par milestone**, lue par le validateur via
`get_milestone_configuration()` (`qbittensor/utils/services/challenges.py:196`)
puis stockée dans `max_solution_runtime_seconds` ; le validateur tue le
conteneur au-delà (`solution_container_manager.py:1083`). Pas de marge, pas de
négociation. Le 560 a été résolu **dans ces 14 400 s** par un concurrent, alors
que notre propre run c169 a mis 17 339 s : notre chaîne est donc ~20 % plus
lente que celle du gagnant, à réglage comparable.

#### 15.2 La loi de débit réelle : décroissance exponentielle non bornée

Run `lim 70/100`, polynôme P, 40,6 M de relations avant arrêt volontaire. Le
débit n'est pas plat : il décroît régulièrement avec le brut déjà produit.

| brut cumulé | débit | | brut cumulé | débit |
|---|---|---|---|---|
| 3,35 M | 25 967 rel/s | | 32,93 M | 23 558 rel/s |
| 9,82 M | 25 591 rel/s | | 40,65 M | 22 910 rel/s |
| 17,52 M | 24 827 rel/s | | | |
| 25,20 M | 24 226 rel/s | | | |

Ajustement `ln(débit)` vs brut sur les 6 points : pente **−0,00355 par M**, soit
**3,55 % par 10 M**, avec une constance remarquable (les 6 points sont alignés).
Aucune saturation sur 40 M.

Loi : `v(R) = 25 967 · exp(−0,00355 · R/M)` et
`T = (exp(kR) − 1) / (k · v₀)`.

Extrapolation au point de complétion `R = 29 × FB = 286,5 M` :
**T ≈ 18 800 s de crible**, avant même le filtrage et l'algèbre linéaire.

#### 15.3 Pourquoi le §13 se trompait : comparaison biaisée

Tous les débits du tableau du §13 ont été mesurés sur la **première bande de q**
`[2,2 M ; 2,4 M)`, c'est-à-dire la bande la plus rapide (c'est la même bande que
la sonde `polytest`). Le 27 632 rel/s de c169 est au contraire une **moyenne sur
420 M**. Comparer un débit instantané optimal à une moyenne de run complet
surestime systématiquement les petits FB — et c'est précisément sur les petits
FB que le §13 concluait.

Preuve que la décroissance dépend fortement de `lim` : en recalant le modèle sur
c169 (`lim 100/150`, 420 M en 15 200 s), on trouve `k ≈ 0,00049 /M`, soit
**7,3× moins** qu'à `lim 70/100`. Plus le FB est petit, plus le débit s'effondre
vite (les petits q faciles s'épuisent). Donc « prendre le plus petit FB possible »
est exactement la mauvaise stratégie.

#### 15.4 Le plancher sur tous les régimes 2LP

Modèle `k(F)` log-linéaire calé sur les deux points mesurés (9,88 M → 0,00355 ;
14,41 M → 0,00049), `v₀(F)` mesuré, `R = 29·F` :

| `lim` | FB | brut | crible prédit | LA | total |
|---|---|---|---|---|---|
| 70/100 | 9,88 M | 286 M | **18 800 s** (mesuré, extrapolé) | 1 035 | 19 800 s |
| 80/120 | 11,46 M | 332 M | 16 100 s | 1 394 | 17 500 s |
| **100/150** | 14,41 M | 418 M | **15 650 s** (calé sur c169 : 15 200 s) | 2 202 | **17 850 s** |
| 120/200 | 17,87 M | 518 M | 15 900 s | 3 505 | 19 400 s |
| 135/230 | 20,0 M | 580 M | 18 300 s | 4 366 | 22 700 s |

Le minimum est un **bassin plat autour de 15 500-16 000 s de crible**, soit
~17 800-19 400 s avec LA. Contre 14 400 s : **23 à 35 % au-dessus**. Et le
filtrage (~1 500-2 500 s pour ~290-420 M de relations sur 24 vCPU) n'est même
pas compté.

Il n'y a donc pas de réglage de `lim` qui sauve la situation.

#### 15.5 La voie 3LP est bloquée en pratique

Le docstring de `gpu/glas_caps_patch.py` décrit la seule voie avec de la marge :
**3 grands premiers à petit `lim`** (`lim 48/67` → 6,84 M de colonnes, N ~6-9 M,
LA ~400-1 000 s). C'est ce que le patch de caps est censé débloquer. Test
effectué :

```
LPB0=32 LPB1=33 MFB0=90 MFB1=92 RLIM=48000000 ALIM=67000000 \
LAMBDA0=2.81 LAMBDA1=2.79 \
GLAS_BUCKET_MARGIN=3 GLAS_SURV_DIV=16 GLAS_HITS_DIV=4
```

Résultat : **19 minutes sans une seule relation**, aucun message d'overflow,
aucune erreur. Le run 2LP équivalent passe sa porte de relations en **132 s**.
C'est le même mode d'échec silencieux que `SIEVE_A=30` (44 min, rien) et
`GLAS_SURV_DIV=32` (75 min, rien).

Interprétation la plus probable : la cofactorisation du cribleur GPU ne sait pas
scinder un cofacteur en **3** premiers ; tous les candidats 3LP sont donc
silencieusement jetés, d'où un débit nul. Les caps n'y changent rien — le patch
agrandit des buffers, il n'ajoute pas la capacité de factorisation manquante.

**Conclusion : la 3LP est hors d'atteinte sur ce build.** Les trois knobs de caps
produisent tous le même blocage ; ce n'est pas un problème de réglage.

#### 15.6 Bilan des leviers, tous fermés

| levier | essai | résultat |
|---|---|---|
| `lim` (balayage complet 48/67 → 135/230) | 10+ runs | optimum ~15 500 s de crible, > budget |
| polynôme (MurphyE) | 20 vs 40 batches | saturé : 1,710e-10 vs 1,642e-10 (bruit) |
| `ncurves` 8 vs 17 | run K | −2,5 % (bruit) |
| caps GLAS (bucket/surv/hits/fcand) | 3 essais | OOM, ou 0 relation |
| `SIEVE_A=30` | 1 essai | 0 chunk en 44 min |
| 3LP (mfb 90/92) | 1 essai | 0 relation en 19 min |
| décroissance du débit | mesurée | 3,55 %/10 M, non bornée |

Il ne reste aucun levier logiciel identifié. Pour tenir 14 400 s il faudrait
**~1,35× le débit** du cribleur actuel, ou un cribleur capable de 3LP.

#### 15.7 Ce qu'il faudrait pour reprendre

1. **Un cribleur GPU qui gère la 3LP** (ou un GLAS corrigé sur ce point) : c'est
   la seule voie qui crée assez de marge (FB 6,84 M au lieu de 14,4 M).
2. **Ou** ~35 % de débit en plus sur la 2LP, ce qu'aucun réglage n'a donné.
3. Le run c169 (560 bits, 17 339 s) montre qu'un concurrent a résolu le 560 en
   ≤ 14 400 s : sa chaîne est ~20 % plus rapide que la nôtre à réglage égal.
   Comprendre cet écart vaut plus que tout réglage de `lim`.

Dépense de la session sur `lol810-maxou2` : **5,08 $** (2,76 $ pour le run
`lim 70/100`, 2,32 $ pour l'essai 3LP).

### 16. CORRECTION du §15.5 : la 3LP n'est pas une impasse de principe (2026-11-02)

Le §15.5 concluait « la cofactorisation du cribleur GPU ne scinde pas en 3
premiers ; la 3LP est hors d'atteinte ». **La lecture du source montre que
c'est la mauvaise formulation.** Trois faits vérifiés :

1. **La cofactorisation de GLAS n'est pas sur le GPU.** Elle est faite sur
   l'hôte par `facul` (la bibliothèque ECM de CADO) :
   `cofactor_cpu()`, `cofactor_finish()`, `facul_all()`
   (`third_party/cado-nfs-public/gpu-siever/src/glas.cpp:1276-1310`).
2. **La logique multi-grands-premiers existe** : `for (klpb = lpb; klpb < s;
   klpb += lpb)` (`:1056-1057`), rejet sur `mfb + marge` (`:909-922`).
3. **Un hook de diagnostic existe et n'est câblé nulle part** :
   `GLAS_COFAC_DUMP=path` (`:1090-1130`) écrit chaque paire de résiduels avant
   `facul` (en-tête 9×u64, puis 4×u64 par candidat).

Donc l'échec 3LP n'est pas un manque de logique : c'est très probablement un
**effondrement du coût de `facul`** sur des résiduels de ~2^85-2^90 (beaucoup de
courbes ECM par candidat → le chunk ne se termine jamais → « 0 relation, aucune
erreur »). La distinction est décisive : « logique absente » serait définitif,
« coût ECM qui explose » est peut-être réglable.

#### 16.1 Le régime correct est la 3LP

La recette c175 **officielle de CADO**, déjà dans l'arbre
(`third_party/cado-nfs-public/gpu-siever/params/params.c175`) :

```
lim0=48.1M lim1=67.6M lpb0=30 lpb1=31 mfb0=60 mfb1=90
```

`mfb1=90` avec `lpb1=31` = **3 grands premiers** côté algébrique. La 3LP est la
norme à c175 ; notre 2LP (`mfb 63/65`) est le compromis imposé par GLAS.

#### 16.2 État vérifié des trois cribleurs

| cribleur | dans l'image ? | 3LP ? | mesure |
|---|---|---|---|
| `glas` | oui | non (0 rel / 19 min) | §15.5 |
| `bench` (cuda-sieve) | **non** — `Dockerfile:10`, retiré le 2026-10-25, source `cuda-sieve/` **non vendored** | oui (`--cofactor`, queue ECM) | indisponible sans re-vendoriser |
| `las` (CPU CADO) | oui — `Dockerfile:84` → `/app/cado-filter/las` | oui (`facul` natif) | **626 rel/s à `-t 14`** à c160 (`factor_c175.sh:379`) → ~50-60× trop lent |

`bench` est perdu, `las` est structurellement trop lent. Seul `glas` est assez
rapide, et c'est le seul qui échoue en 3LP.

#### 16.3 Diagnostic `GLAS_COFAC_DUMP` — FAIT le 2026-11-02, résultat décisif

Run `diag_3lp_cofac.py` (app `ap-h4hBlkVCgz6S1vJOjkaGNu`), 240 s, `lim 48/67
mfb 90/92`, polynôme P, bande `q ∈ [2,2 M ; 2,4 M)`. Trois mesures :

**(a) Le GPU déborde à chaque q, avec des caps déjà énormes.**

```
# GPU overflow at q=2200717 (caps surv=8388608 hits=67108864); falling back to CPU
```

36 overflows sur 22 q en 240 s, à `surv=2^23` / `hits=2^26`. Et :

```
# Sieving side-1 q=2200013; ... 1718805 survivors
```

**1,72 M de survivants pour un seul q** (quelques dizaines de milliers en 2LP).
Avec `mfb=90`, `r = min(lambda·lpb, mfb+8) ≈ 90 bits` est si permissif que la
population explose. Aucun cap raisonnable ne la contient : c'est structurel.

**(b) Le repli CPU donne 46 rel/s.**

| | 2LP `lim 48/67` (run I) | 3LP `lim 48/67` |
|---|---|---|
| relations en 240 s | ~1,12 M | **11 163** |
| débit | 4 658 rel/s | **46,5 rel/s** |

199 M de relations à 46,5 rel/s = **4,26 M s ≈ 49 jours**.

**(c) `facul` accepte 0,27 % des candidats.**

4 094 586 candidats → 11 163 relations. Résiduels mesurés
(`tools/cofac_dump_stats.py`) : côté 0 médiane **84 b** (p90 89, max 90), côté 1
médiane **87 b** (p90 92, max 92) ; 89,8 % / 94,6 % nécessitent une chaîne 3LP.
Avec `ncurves=17` (calibré 2LP), `facul` n'en scinde que 0,27 %.

**Verdict.** L'hypothèse du §15.5 (« la cofactorisation GPU ne scinde pas en 3
premiers ») est **fausse** : elle est sur l'hôte, elle reçoit bien les candidats,
elle en accepte quelques-uns. Le blocage est **double et cumulatif** : (1) le GPU
déborde structurellement à `mfb=90` → repli CPU à 46 rel/s ; (2) `facul` à
`ncurves=17` est très en dessous du régime 3LP. **Le point (1) suffit à condamner
la 3LP sur GLAS**, indépendamment du point (2).

Le découplage crible/cofactorisation (§16.4) ne traiterait que (2) : même avec
une cofactorisation parfaite et gratuite, on resterait à 46 rel/s côté crible.
Il faudrait **d'abord** que GLAS tienne 1,7 M de survivants par q, ce qui suppose
une refonte de son buffer de survivants — hors de portée sur un binaire patché.

Coût du test : un run de 5 min, ~0,05 $. Meilleur rapport information/coût du
projet : il a évité un run 3LP de 4 h qui aurait échoué.


#### 16.4 Le découplage crible/cofactorisation ne suffirait pas

C'était l'idée tirée du papier Miele-Bos-Kleinjung-Lenstra (CHES 2014, ePrint
2014/397), et la mesure la disqualifie comme remède principal : elle ne traite
que le point (c), `facul` à `ncurves=17`. Le point (a) est **en amont** — le GPU
déborde et ne produit ses survivants qu'en repli CPU.

Même avec une cofactorisation parfaite et gratuite, on resterait à ~46 rel/s côté
crible. Pour rouvrir la 3LP il faudrait **d'abord** que GLAS tienne 1,7 M de
survivants par q sans déborder : une refonte du buffer de survivants (dimensionné
par bande, pas par q), pas un réglage. GLAS étant un binaire Cognition patché,
ce n'est pas dans nos moyens actuels.

Ordre correct si quelqu'un reprend : (1) buffer de survivants, (2) `ncurves` 3LP,
(3) découplage. Le (1) seul est bloquant.


#### 16.5 Références triées (ne pas perdre de temps)

- **ePrint 2021/141 (Ducas-Stevens-van Woerden, Tensor Cores) : HORS SUJET.**
  C'est du lattice sieving au sens **SVP / G6K**, pas NFS. Aucun rapport avec
  GLAS. C'était la référence présentée comme la plus importante.
- **github.com/pstach/gls** : prototype OpenCL, son propre README dit « not as
  fast as CADO's lattice siever ». Inutilisable.
- **arXiv 2001.10860 (McGuire-Robinson)** : réel, énumération 3D, mais GLAS
  crible en 2D — inexploitable sans réécrire le cœur.
- **ePrint 2014/397** : la seule utile, pour l'architecture (16.4).
- **params.c175 de CADO** : la plus utile de toutes (16.1).

Détail complet dans `../JOURNAL_TENTATIVES.md` §11.

### 17. Comparaison avec le solveur 560 du dépôt (2026-11-02)

Le dépôt contient `rsa560_solver/` — l'archive de soumission du 560, qui a
réellement fonctionné. C'est la référence locale, et elle n'avait jamais été
comparée ligne à ligne. Trois résultats.

#### 17.1 Les deux pipelines sont quasi identiques

```
1687  rsa560_solver/pipeline_c169/factor_c169.sh
1689  rsa580_solver/pipeline_c169/factor_c175.sh
```

Le diff ne porte que sur la gestion des variables `RSA580_*` (et l'ajout de
`LPB1=34`). **L'écart de performance ne vient donc pas du code** : c'est un
problème de réglage ou de polynôme.

#### 17.2 Défaut corrigé : l'image 580 embarquait la pire configuration connue

`Dockerfile:121` disait :

```
ENV RSA580_LPB1=34 ... RSA580_MFB1=68 RSA580_MFB0=64 RSA580_ALIM=600000000 RSA580_RLIM=250000000
```

soit `lim 250M/600M` → **FB ≈ 45,2 M de colonnes** → `raw ≈ 29 × FB ≈ 1,31 G`
→ **~38 700 s** (cf. tableau §9). C'est-à-dire 2,7× le budget : **l'image de
soumission livrait exactement la configuration qui avait échoué le 31/10.**

Corrigé en :

```
ENV RSA580_LPB1=33 RSA580_LPB0=32 RSA580_MFB1=66 RSA580_MFB0=64 RSA580_ALIM=150000000 RSA580_RLIM=100000000
```

soit `lpb 32/33, mfb 64/66, lim 100M/150M, lambda 2.0352/2.0379` — le jeu de
production **560** documenté (`rsa560_solver/pipeline_c169/README.md:28`,
mesuré le 2026-10-17) et aussi le meilleur point de notre propre balayage 580
(FB 14,41 M → 418 M raw → ~14 100 s de crible + ~2 200 s de LA). Toujours ~13 %
au-dessus du budget, mais **2,4× meilleur** que 250/600, et c'est la bonne base
pour reprendre.

Résolution vérifiée par simulation : `lpb 32/33 mfb 64/66 lim 100M/150M
lambda 2.0352/2.0379`.

#### 17.3 Piège : ne pas copier le défaut du script 560

`factor_c169.sh:170` porte `RLIM=200M ALIM=450M`, justifié par
« +8,8 % / +13,4 % / +15,1 % rel/s à q 2,2M / 12,5M / 22,4M vs 100M/150M ».
**Ce commentaire optimise le rel/s, pas le temps total** : à FB 34,9 M il faut
~1,01 G de relations, donc c'est plus lent de bout en bout. C'est exactement
l'erreur qui a coûté le run du 31/10. Le défaut a donc été explicitement écrasé
dans l'image 580 (§17.2).

#### 17.4 Les mesures du 580 ont été faites hors profil de production

Tous les runs du 580 sont passés par `modal_rsa580.py`, qui ne pose **pas**
`CONTAINER=1`. Ils ont donc utilisé les défauts hors conteneur :
`NCPU=24, SIEVE_T=20`. Le profil de production (`factor_c169.sh:48-90`) pose
`NCPU=20, SIEVE_T=16, SIEVE_HOST_T=4, INC_PAR=3, PROBE_NT=12, DUP2_PAR=4,
INC_TPG=3`, plus les réglages du contrôleur d'arrêt (`STOP_SHAPE=1
STOP_NFAC=0.246 STOP_PROBE_TAX=6 STOP_PROBE_EVERY=2 FIRST_PROBE_AUTO=1`).

Conséquence : nos débits sont ceux d'une chaîne **légèrement différente** de
celle que le validateur exécuterait. L'écart est probablement faible (glas ne
consomme que ~3,3 cœurs quel que soit `-t`, et nos sondes étaient rares), mais
il n'a jamais été mesuré.

#### 17.5 La piste sérieuse : un écart de débit de ~1,35× inexpliqué

Le commentaire de `factor_c169.sh:73` documente une mesure de production :

> « gpu/key1m.env, blind GCP key 31 at 32/33: **14 774 s wall, 485 M raw, N 16,8 M** »

485 M de relations pour **14 774 s de bout en bout** (crible + filtrage + LA +
sqrt). Si le crible occupe ~80 % de ce temps, cela implique **~40 000 rel/s**.

Or notre mesure à `lim 100/150`, polynôme P (MurphyE 1,642e-10), donne
**29 614 rel/s** sur la même bande (§13). Soit **~1,35× d'écart** — précisément
l'ordre de grandeur qui manque au 580.

Trois explications possibles, non départagées :

1. **Le profil** : `CONTAINER=1` (SIEVE_T=16) vs nos `SIEVE_T=20` ;
2. **Le polynôme** : la production 560 utilise `PS_BATCHES=3` + sopt/ropt, dont
   le MurphyE n'est pas comparable à notre P (nous saturons à 1,7e-10 avec
   `PS_ADAPT`, mais la production passe par ropt/sopt, un autre chemin) ;
3. **L'instance** : « blind GCP key 31 » est un N aveugle, pas forcément le
   challenge 560 lui-même.

**Test qui tranche, et il est bon marché** : relancer le 580 à `lim 100/150`
sous `CONTAINER=1`, polynôme P, et mesurer le débit sur la même bande de q.
S'il monte de 29,6 k à ~38-40 k rel/s, c'est le profil. Sinon, c'est le
polynôme ou l'instance.

Enjeu : à 38 000 rel/s, `418 M / 38 000 = 11 000 s` de crible + 2 200 s de LA =
**13 200 s → le 580 tient dans 14 400 s.** C'est la seule voie restante qui
pourrait faire passer le palier, et elle ne demande aucun code nouveau.

**Correction au §12** : l'« incohérence » signalée (17 339 s > 14 400 s) est
levée. Le point 15 200 s + 2 139 s est une mesure ancienne ; la mesure de
production plus récente donne **14 774 s wall**, soit 2,6 % au-dessus de la
limite — donc le 560 était bien à portée, et notre chaîne l'est presque aussi.

### 18. Test du profil et découverte de GLAS_ADJUST (2026-11-02)

Suite du §17 : le profil `CONTAINER=1` (`SIEVE_T=16`, `NCPU=20`) pouvait-il
expliquer l'écart de débit ? Trois runs instrumentés, même bande
`q ∈ [2,2 M ; 2,4 M)`, `lim 100M/150M`, polynôme P, `-A 29`.

#### 18.1 Le profil de threads n'explique rien : ratio exactement 1,000

| bras | relations (180 s) | débit |
|---|---|---|
| `-t 16` (profil de production) | 2 766 971 | 15 372,1 rel/s |
| `-t 20` (ce qu'on utilisait) | 2 766 972 | 15 372,1 rel/s |

**Ratio 1,000**, à une relation près. `glas -t` ne pilote que les threads hôte
(facul + travail hôte), et glas ne consomme que ~3,3 cœurs quel que soit `-t`
(cf. le commentaire de `factor_c169.sh:77`). **L'hypothèse « c'est le profil »
est morte.**

#### 18.2 Ce qui explique l'écart : `GLAS_ADJUST`

Les 15 372 rel/s ci-dessus sont très en dessous des ~29 600 attendus au même
`lim`. La cause est que le binaire compile les patchs avec des défauts
**inactifs** :

```c
/* glas-adjust-strategy.patch:25 */
static int const v = getenv("GLAS_ADJUST") ? atoi(getenv("GLAS_ADJUST")) : 0;
```

`GLAS_ADJUST` vaut donc **0** si on ne le pose pas, et le pipeline le pose à 3
(`factor_c175.sh:183`). Isolation, tous les autres `GLAS_*` du pipeline posés :

| configuration | débit | gain |
|---|---|---|
| `GLAS_ADJUST=0` | 15 372 rel/s | — |
| `GLAS_ADJUST=0` + les 10 autres `GLAS_*` | 15 372 rel/s | **1,000×** |
| `GLAS_ADJUST=3` | 22 037 rel/s | **1,434×** |
| `GLAS_ADJUST=3 GLAS_ADJUST_SQUEEZE=3` | 23 088 rel/s | +4,8 % |

Deux enseignements :

1. **`GLAS_ADJUST=3` vaut 1,43×.** C'est le plus gros levier unitaire du
   cribleur, et il était déjà actif dans le pipeline — mais **toute mesure faite
   avec un `glas-gpu` invoqué à la main est 43 % trop basse**. C'est le piège qui
   a rendu mes trois premiers diagnostics (§11.5, 18.1) incomparables au
   pipeline.
2. **Les 10 autres `GLAS_*` ne donnent rien à ce `lim`** (15 372 dans les deux
   cas). Les gains documentés par patch (−2,6 %, −4,7 %, −7,9 %…) ont été
   mesurés à d'autres régimes ; ils ne se cumulent pas ici.

#### 18.3 Gain gratuit adopté : `GLAS_ADJUST_SQUEEZE=3`

Le patch laisse `GLAS_ADJUST_SQUEEZE` à **1** alors que CADO utilise **3**
(« each step halves I and doubles J »). Mesuré : **+4,8 %**. Aucun des deux
pipelines ne le réglait. Adopté comme défaut dans `factor_c175.sh`.

#### 18.4 ⚠ Désaccord de mesure — TRANCHÉ le 2026-11-02

La mesure directe donnait **23 088 rel/s** à `lim 100M/150M` avec `ADJUST=3
SQUEEZE=3`, alors que le §13 tabulait **29 614 rel/s** au même `lim`, même
polynôme, même bande. **Les deux ne pouvaient pas être vrais.**

Mesure longue (`diag_rate_long.py`, app `ap-CCzmtAEqqXUA7Fz9rOPArE`), 901,6 s,
un seul processus glas, horodatage hôte, échantillonnage toutes les 30 s :

| t (s) | cumul | débit de fenêtre | cumul moyen |
|---|---|---|---|
| 30 | 754 318 | 25 144 | 25 144 |
| 90 | 2 368 585 | **26 946** (pic) | 26 288 |
| 180 | 4 724 243 | 25 766 | 26 202 |
| 300 | 7 824 046 | 25 792 | 26 037 |
| 601 | 15 339 130 | 24 664 | 25 527 |
| 901 | 22 515 558 | 23 431 | **24 973** |

- **moyenne 901,6 s : 24 973 rel/s** ; état stationnaire (421 dernières s) :
  **24 117 rel/s**.
- **Le pic de fenêtre est 26 946 rel/s : 29 614 n'est atteint dans aucune
  fenêtre.** Le chiffre du §13 est donc **réfuté**.
- La décroissance est réelle : 26 946 → 23 431 sur ~20 M de relations, soit
  **~−6,2 % par 10 M** (ajustement log-linéaire sur 8 points).
- Variance inter-runs : la même config mesurée à 180 s donnait 23 088 puis
  26 202 rel/s, soit **13 % d'écart**. Toute mesure courte est donc à ±13 %.

**Conséquences, et elles sont défavorables :**

1. À 24 973 rel/s constants, `418 M / 24 973 = 16 740 s` de crible + ~2 200 s
   de LA = **~18 900 s**, soit **31 % au-dessus** du budget. Avec la
   décroissance mesurée c'est pire.
2. La projection optimiste du §17.5 (« 13 200 s, le 580 tient ») est **close**.
3. L'« écart de 1,35× » avec la chaîne 560 s'explique très probablement par la
   **taille de N** : à 560 bits les normes sont plus petites, donc plus de
   relations par q au même `lim`. Ce n'est pas un défaut à corriger.

**Méthode à retenir** : ne jamais dériver un débit de `relq` (relations par
unité de q, `factor_c175.sh:1561`) ; toujours mesurer des relations par seconde
horodatées côté hôte, sur ≥ 10 min et plusieurs fenêtres.









