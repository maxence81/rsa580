# RSA-580 / Enigma Subnet 63 — dépôt de reprise

**Dépôt : <https://github.com/maxence81/rsa580>** (public)

```bash
git clone https://github.com/maxence81/rsa580.git enigma_rsa
```

Factorisation d'un semi-premier **580 bits** (~175 chiffres, `c175`) par GNFS,
sous la contrainte dure de **14 400 s** (4 h) du validateur Enigma SN63, sur
RTX PRO 6000 96 Go / 24 vCPU / 85 Go RAM, `--network none`, `--read-only`,
`/tmp` en tmpfs 10 Go.

**Statut : non résolu. Le verdict « hors de portée » est ROUVERT (2026-11-02).**
La chaîne GLAS 2LP — celle du 560, présente ici sous `rsa560_solver/` — est bien
condamnée par la mesure (§6.2 : 23 244–23 942 s pour 14 400 s). Mais le dossier
avait été clos sur la prémisse « aucun cribleur GPU capable de 3LP n'est
disponible » — **cette prémisse est fausse** : `cuda-sieve` est domaine public
(CC0), gère la 3LP des deux côtés avec rho/ECM automatique, tourne sur sm_120, et
**ses binaires sont dans le zip de la solution 530 bits**. Voir `SOLUTIONS_DIFF.md`.
Deux voies, désormais nommées : **A** rester sur GLAS 2LP (mesuré insuffisant),
**B** passer en 3LP sur GPU (jamais mesuré à c175). Le prochain jalon est une
mesure de débit 3LP, pas un chantier de plusieurs semaines.

---

## 1. Verdict en une page

| question | réponse mesurée |
|---|---|
| La limite est-elle vraiment 14 400 s ? | **Oui**, dure, par milestone. Confirmé par l'API publique des challenges (`max_solution_runtime = 14400`), tuée par `solution_container_manager.py:1083`. |
| Le 560 bits a-t-il été résolu dans ce budget ? | **Oui**, par un concurrent (30 soumissions). Notre run c169 met 17 339 s et notre mesure *blind GCP* 14 774 s, alors que notre propre cible était ≤ 13 000 s → notre chaîne est marginale **déjà** sur le 560. |
| Quelle config le 560 expédié utilise-t-il ? | **`lim 200M/450M`, `lpb 32/33`**. Son `Dockerfile` ne fixe ni `RLIM` ni `ALIM` : les défauts de `factor_c169.sh:170` s'appliquent. Le « 420 M à `lim 100/150` » d'un commentaire décrit le profil 530 du 17/10, pas le profil expédié. |
| Combien de relations le 580 doit-il produire ? | **441 M au croisement, 485 M brutes.** Le besoin est indexé par `lpb` (32/33), **pas par `lim`** : `stop_cost.py:193-195`, *« lim/lambda variants reach the same count sooner (same relations needed) »*. |
| Combien coûte le 580 en 2LP ? | **23 244 à 23 942 s, mesuré** sur le profil expédié du 560 (`lim 200M/450M`, `mfb 62/64`). Soit **+61 à +66 %**. Le profil `100M/150M` donne ~20 800 s par arithmétique : les deux dépassent largement le budget. |
| `lim 200M/450M` aide-t-il ? | **Non, il déplace le travail.** Pic à 27 658 rel/s en début de plage, mais moyenne cumulée **22 194 rel/s**, soit −11 % sous les 24 973 rel/s de `100M/150M`. Décroissance de −133 rel/s par chunk, bien plus raide qu'à `100/150`. |
| Où en est le budget ? | À 14 400 s, le crible aurait produit **~304 M** relations sur les **441 M** requises, soit **68,9 %**. Le budget expire avant le croisement, avant même le filtrage et la LA. |
| La loi `raw ≈ 30 × FB` tient-elle ? | **Non, elle est retirée.** Elle ne valait que pour le profil 530 (`lim 100/150`, FB 14,03 M). Au profil expédié : FB 34,92 M, 441 M de croisement ⇒ **r ≈ 13**. |
| La 3LP peut-elle sauver la mise ? | **Non.** Mesuré à **46,5 rel/s** contre 4 658 en 2LP : le GPU déborde à chaque q (1,72 M de survivants par q) et retombe sur un repli CPU. 199 M de relations → ~49 jours. |
| Et un second GPU ? | **Non, par spécification.** Le validateur alloue **un seul** RTX PRO 6000 96 Go (`--gpus all` ne donne que ce que le nœud a). Il fallait ~1,5× d'agrégat. |
| Reste-t-il un réglage ? | **Non.** `lim` (10+ runs), polynôme (saturé, ropt+sopt déjà actifs), `ncurves` (bruit), caps GLAS (OOM ou 0 relation), `SIEVE_A=30` (rien), threads (ratio 1,000), 3LP (fermé), GPU (spec). |
| Que faudrait-il ? | **~1,6× le temps total**, ou ~1,5× sur le crible seul. Aucune voie disponible ici (§6). |
| Y a-t-il eu un gain réel ? | **Oui** : `GLAS_ADJUST_SQUEEZE=3` (+4,8 %), adopté, et `GLAS_ADJUST=3` confirmé à 1,434×. |

Le détail chiffré, run par run, est dans `JOURNAL_TENTATIVES.md` (14 sections,
**§14 = le run de mesure qui clôt le dossier**, §13.8 = corrections après revue
contradictoire) et `rsa580_solver/HANDOFF.md` (§16 corrige §15, §19 clôt le
dossier, §19.8 corrige §19.3).

---

## 2. Structure du dépôt

```
enigma_rsa/
├── README.md                  ← ce fichier (point d'entrée)
├── JOURNAL_TENTATIVES.md      ← journal des 8 phases + revue de littérature
├── modal_rsa580.py            ← runner Modal du 580 (POLY_B64, ENV_EXACT)
├── diag_3lp_cofac.py          ← diagnostic 3LP (GLAS_COFAC_DUMP)
├── probe_profile.py           ← sonde zéro-coût pour tester un workspace
├── cof_3lp_stats.txt          ← résultat du diagnostic 3LP (preuve)
├── rsa580_solver/             ← LE solveur 580 (work in progress)
│   ├── Dockerfile             ← image de soumission (glas + CADO + gpu_la)
│   ├── pipeline_c169/
│   │   ├── factor_c175.sh     ← pipeline 580 (dérivé de c160/c169)
│   │   ├── factor_c169.sh     ← pipeline 560, référence qui a produit 420 M rel
│   │   └── stop_cost.py       ← contrôleur d'arrêt (⚠ lire §3.1 avant de le croire)
│   ├── gpu/                   ← patches GLAS (caps, session, xfuse, region…)
│   ├── third_party/cado-nfs-public/   ← arbre CADO Cognition b5ca9c4 + gpu-siever
│   └── tools/cofac_dump_stats.py      ← parseur de dump de cofactorisation
└── rsa560_solver/             ← LE SOLVEUR 560 COMPLET (référence qui marche)
```

`rsa560_solver/` est l'archive de soumission du 560 bits décompressée (elle
s'appelait `964dd74e-…/rsa560_solver`, renommée ici ; aucun chemin du code ne
la référençait). C'est **le point de comparaison le plus utile** : même
Dockerfile, même pipeline, mêmes patches, réglé pour un N plus petit.

---

## 3. Ordre de lecture pour reprendre

1. **`JOURNAL_TENTATIVES.md`** — ce qui a été tenté, dans l'ordre, avec les
   chiffres. Lire §7 (la mesure décisive) et §11 (la 3LP).
2. **`rsa580_solver/HANDOFF.md`** — le relais technique. Lire §1 (le piège du
   prédicteur), §9–10 (modèle de coût), **§15** (verdict), puis **§16** qui
   corrige §15 sur la 3LP.
3. **`rsa580_solver/pipeline_c169/factor_c175.sh`** — le pipeline réel. Le bloc
   de commentaires 120–200 contient l'historique des réglages mesurés.

### 3.1 Deux pièges qui ont coûté des runs entiers

- **`stop_cost.py` clampe** son point de sonde prédit dans
  `[PROBE_AT + PROBE_STEP/2, PROBE_AT + 4×PROBE_STEP]`. Quand le vrai crossover
  est plus loin, la valeur rapportée **est exactement le plafond**
  (`last + 4×PROBE_STEP`). C'est arrivé deux fois. Ne jamais lire ce nombre
  comme une estimation — recalculer sur la pente d'excès mesurée.
- **`modal run --detach` ne survit pas au SIGTERM du client.** Trois apps, dont
  deux runs complets, ont été tuées en fin d'appel shell. **Toujours lancer en
  tâche de fond.**

---

## 4. Lancer quelque chose

### 4.1 Prérequis Modal (deux pièges d'environnement)

```bash
# 1) le bac à sable exporte un proxy que Modal >= 1.6 honore et qui exige
#    python-socks (absent) -> "Could not connect to the Modal server"
#    et "profile misconfigured" sur TOUS les profils. Retirer les variables :
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
    -u ALL_PROXY -u all_proxy \
    "C:/Users/maxen/AppData/Local/Programs/Python/Python310/python.exe" -m modal ...
```

```python
# 2) l'image builder 2026.10 n'accepte plus Python 3.10 : toute image
#    IMPLICITE (fonction sans image=) doit fixer python_version="3.11".
#    Les images from_dockerfile ne sont pas concernées.
modal.Image.debian_slim(python_version="3.11")
```

Cache d'images : **par workspace**. Un workspace neuf repaie ~40 min de
compilation CADO. Changer une variable `GLAS_*` ne reconstruit que la petite
couche `.env`.

### 4.2 Le diagnostic 3LP (5 min, ~0,3 $)

```bash
cd /c/Users/maxen/enigma_rsa
env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy \
    -u ALL_PROXY -u all_proxy \
  "C:/Users/maxen/AppData/Local/Programs/Python/Python310/python.exe" \
  -m modal run ./diag_3lp_cofac.py
# puis
python rsa580_solver/tools/cofac_dump_stats.py cof_3lp.bin
```

### 4.3 Un run 580 complet

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

> ⚠ `lim 70/100` **ne tient pas** : c'est la config du run qui a mesuré la
> décroissance de débit (3,55 %/10 M) et réfuté le §13. Le plancher est plutôt
> `lim 100/150`–`120/200`. Voir `JOURNAL_TENTATIVES.md` §7.

---

## 5. Ce qui est fermé, et pourquoi (à ne pas refaire)

| levier | essais | résultat |
|---|---|---|
| `lim` 48/67 → 135/230 | 10+ runs | plancher ~15 500–16 000 s de crible > budget |
| polynôme (MurphyE) | 20 vs 40 batches | saturé : 1,710e-10 vs 1,642e-10 (bruit) ; ropt + sopt **déjà actifs** |
| `ncurves` 8 vs 17 | run K | −2,5 % (bruit) |
| caps GLAS (margin/surv/hits/fcand) | 4 essais | OOM CUDA, ou 0 relation |
| `SIEVE_A=30` | 1 essai | 0 chunk en 44 min |
| profil de threads `-t 16` vs `-t 20` | A/B 180 s ×2 | ratio **exactement 1,000** — aucune marge CPU |
| 3LP `mfb 90/92` | 4 essais | **46,5 rel/s**, GPU déborde à chaque q |
| découplage crible/cofactorisation | analyse | ne traite pas le blocage principal (§16.4) |
| McGuire-Robinson | analyse | accélère l'énumération, pas le filtre à survivants (§12) |
| **nombre de GPU** | spec | **un seul** RTX PRO 6000 alloué ; la chaîne n'en piloterait qu'un |
| grâce du validateur | mesure | **~30 s** (`SOLUTION_CONTAINER_MANAGER_TIMEOUT`) |
| **`GLAS_ADJUST`** | A/B | **gagné** : 1,434× — déjà `=3` par défaut |
| **`GLAS_ADJUST_SQUEEZE`** | A/B | **gagné** : +4,8 % — adopté à `=3` le 02/11 |

**La 3LP — le seul régime qui créerait de la marge — est fermée par une limite
structurelle** : avec `mfb=90`, GLAS produit 1,72 M de survivants pour un seul q
(quelques dizaines de milliers en 2LP), déborde même à `surv=2^23`, et retombe
sur un repli CPU à 46 rel/s. Il faudrait une refonte de son buffer de
survivants — GLAS est un binaire Cognition patché, pas un projet refondable ici.

---

## 6. Ce qui rouvrirait le dossier

Le budget est arrêté (§1). Les seules conditions de réouverture, par ordre de
plausibilité :

1. **Un cribleur GPU qui gère la 3LP** — c'est-à-dire dont le buffer de
   survivants ne déborde pas à 1,72 M par q. Ce n'est pas un réglage de GLAS :
   c'est un autre binaire. C'est la seule voie avec une marge confortable, le
   régime 3LP divisant le besoin en relations par ~2,5. Rien de tel n'est
   disponible ici : `bench`/cuda-sieve a été retiré du Dockerfile le 2026-10-25
   et sa source n'est plus vendored ; `las` (CPU) gère la 3LP mais tourne à
   626 rel/s à `-t 14` à c160, soit ~50× trop lent.
2. **Une machine à plusieurs GPU** — ~1,5× sur le crible suffit, et le code
   actuel ne sharde pas (`factor_c175.sh:196`, une seule session glas). Il
   faudrait router les bandes q sur N sessions FIFO (`i mod N`) et remplacer le
   test d'existence `nvidia-smi -L` (ligne 541) par un comptage. Sans regret :
   repli sur un device si un seul est visible. **Inutile pour ce challenge**,
   dont la spec n'alloue qu'un GPU — mais c'est le seul chemin de débit non
   mathématique qui reste.
3. **Comprendre l'écart de 20 % avec le concurrent sur le 560** — piste la plus
   faible : même comblée intégralement, elle ne donne que 1,20× contre ~1,5×
   requis. Ce qui n'est pas publié, c'est le code du **concurrent** (le dépôt
   officiel des solutions s'arrête au 500 bits) ; ce n'est donc pas une source à
   lire mais un write-up externe à chercher. À ne pas confondre avec
   `rsa560_solver/`, qui est **notre** chaîne 560, présente dans ce dépôt et
   directement exécutable — c'est elle qui a été mesurée en §6.2.

### 6.1 Deux points autrefois « ouverts », désormais tranchés

- **L'« écart de 1,35× » avec la chaîne 560** n'était pas un défaut. Mesure
  longue du 2026-11-02 (901,6 s, horodatage hôte) : **24 973 rel/s** en moyenne,
  24 117 en régime stationnaire, pic de fenêtre 26 946. Le chiffre de 29 614 du
  §13 du journal est **réfuté** — jamais atteint. L'écart s'explique par la
  taille de N : à 560 bits les normes sont plus petites, donc plus de relations
  par q au même `lim`. Voir `HANDOFF.md` §18.4 et §19.
- **Le budget est désormais mesuré, plus estimé** : 485 M de relations brutes à
  `lpb 32/33` (441 M au croisement), et 22 194 rel/s de moyenne cumulée au profil
  `200M/450M`. Total **23 244 à 23 942 s**, +61 à +66 % (§6.2). Toute projection
  antérieure — 29 614 rel/s, 420 M, « +5,9 % de gain », « ~20 600 s » — est à
  jeter.

### 6.2 Le chiffre qui manquait : il a été mesuré

Le run a été lancé le 2026-11-02 (app `ap-IbEl9TQebT7CNj5W93nLjG`) : chaîne 560
en config expédiée (`lim 200M/450M`, `mfb 62/64`) appliquée au N de 580 bits,
polyselect normal, `WALL_TIME` non fixé, plafond 7 h 30. Il a été **interrompu
volontairement à 12 160 s** de crible, la conclusion étant déjà acquise.

```
269 873 541 relations à 12 160 s   →   22 194 rel/s en moyenne cumulée
pic 27 658 rel/s (chunk 4)         →   pente −133 rel/s par chunk
```

À 14 400 s, le budget n'autorise que **~304 M** relations pour un besoin de
**441 M** : **68,9 %**, soit **1,45× de déficit en relations**, avant filtrage et
algèbre linéaire. Total projeté **23 244 à 23 942 s** (+61 à +66 %), et la borne
la plus favorable — débit gelé à 20 591 rel/s, LA gratuite — reste à **+46 %**.

Correction importante que ce run a produite : `lim 200M/450M` **n'est pas** un
levier de débit. Le pic de début de plage (27 658) est un artefact ; la moyenne
cumulée (22 194) est **11 % sous** les 24 973 rel/s de `100M/150M`, et la
décroissance y est bien plus raide. Le « +5,9 % » annoncé à mi-parcours était
faux, comme l'était le total de ~20 600 s qui en découlait.

Détail chunk par chunk, pente, relevés mémoire : `JOURNAL_TENTATIVES.md` §14.

---

## 7. Comptes Modal

| profil | état (2026-11-02) |
|---|---|
| `lol810-maxou2` | **OK**, utilisé pour les derniers runs |
| `lol810-maxou` | ~42,67 $ dépensés, plafond atteint |
| `maxence81` | 0,00 $ mais plafond à 0 → refusé |
| `maxence7567`, `maxence-dabrowski81` | workspace en pause |

Aucun profil ne peut être débloqué en CLI : le plafond et la pause sont des
actions du dashboard. Un run 580 complet de 4 h coûte **~6–7 $**.

---

## 8. Contrat de sortie du validateur (rappel)

L'image est construite par le validateur depuis le zip de soumission, avec ce
`Dockerfile` à la racine. stdout doit contenir : les logs, le séparateur
`SOLUTION_OUTPUT_SEPARATOR`, puis un zip base64 avec au minimum `result.json`
(`status`, `p`, `q`) et `solve_info.json`. Toute modification du Dockerfile doit
préserver ce contrat.
