# Vícepáskový Turingův stroj pro výpočet binárního součinu n‑tice čísel

Semestrální projekt – **XTILO**  

---

## 1. Úvod

Cílem projektu je konstrukce vícepáskového deterministického Turingova stroje realizujícího výpočet binárního součinu n‑tice čísel. Návrh klade důraz na korektnost, čitelnost a možnost detailního sledování výpočtu prostřednictvím krokového výpisu konfigurací stroje.

---

## 2. Formální specifikace problému

### 2.1 Vstup

Vstupem je řetězec tvaru:

```
#b₁#b₂#…#bₙ##
```

kde:

- `bᵢ ∈ {0,1}*` je binární reprezentace nezáporného celého čísla,
- symbol `#` slouží jako oddělovač,
- vstup je vždy ukončen dvojicí `##`.

Příklady:

- `#101#11##`  (5 × 3)
- `#111#11#10##` (7 × 3 × 2)
- `#0#101##` (0 × 5)
- `#1##` (1)

### 2.2 Výstup

Výstupem je binární reprezentace čísla:

```
b₁ × b₂ × … × bₙ
```

zapsaná **bez nul** (s výjimkou výsledku `0`).

---

## 3. Algoritmus

1. Binární čísla ze vstupu jsou postupně převáděna do **unární reprezentace**.
2. Násobení je realizováno jako **opakované sčítání v unárním tvaru**.
3. Výsledný unární součin je převeden zpět do **binární reprezentace**.
4. Výsledek je zapsán na samostatnou výstupní pásku.

---

## 4. Turingův stroj

### 4.1 Počet pásek

Stroj používá **pět pásek**:

| Páska | Označení | Úloha |
|---|---|---|
| T0 | **IN** | Vstupní páska (binární čísla) |
| T1 | **ACC** | Akumulátor – průběžný součin (unárně) |
| T2 | **FAC** | Aktuální faktor (unárně) |
| T3 | **SCR** | Pomocná pracovní páska |
| T4 | **OUT** | Výstupní páska (binární výsledek) |

Každá páska má **jednoznačně danou roli**, což zjednodušuje návrh přechodové funkce.

---

## 5. Abeceda stroje

### 5.1 Vstupní abeceda

```
Σ = {0, 1, #}
```

### 5.2 Pásková abeceda

```
Γ = {0, 1, #, L, X, Y}
```

### 5.3 Význam symbolů

| Symbol | Význam |
|---|---|
| `0`, `1` | binární číslice |
| `#` | prázdný symbol (blank) a zároveň oddělovač |
| `L` | levá kotva unárního bloku (marker začátku) |
| `X` | dočasné označení zpracované unární jednotky |
| `Y` | pomocná značka při zdvojování / obnově |

Pomocné symboly (`L`, `X`, `Y`) se používají pouze na interních pracovních páskách (ACC/FAC/SCR).

---

## 6. Role jednotlivých pásek

### 6.1 IN (T0)

- obsahuje neměnný vstup,
- stroj z ní pouze čte.

### 6.2 FAC (T2)

- obsahuje právě zpracovávaný faktor v unární podobě,
- vzniká převodem aktuálního binárního čísla ze vstupu,
- po použití je vymazána.

### 6.3 ACC (T1)

- obsahuje průběžný výsledek násobení v unární reprezentaci,
- je opakovaně aktualizována operací `ACC := ACC × FAC`,
- po dokončení výpočtu je při převodu do binární podoby vyprázdněna (zůstane čistá).

### 6.4 SCR (T3)

- pomocná páska pro kopírování, dočasné značkování a přeuspořádání,
- slouží např. při:
  - násobení (opakované sčítání / kopírování unárních bloků),
  - převodu unárního výsledku na binární,
  - čištění a obnově značek.
- na konci výpočtu je prázdná.

### 6.5 OUT (T4)

- obsahuje finální výsledek,
- výstup je zapsán **binárně, MSB first**,
- páska neobsahuje žádné pomocné symboly.

---

## 7. Fáze výpočtu

Výpočet je rozdělen do logických fází:

### Inicializace
- nalezení prvního čísla na vstupu,
- inicializace pracovních pásek.

### Převod bin → unary (do FAC)
- převod binárního čísla do unární reprezentace na pásce FAC (s kotvou `L`).

### Unární násobení
- realizace operace `ACC := ACC × FAC` (unárně),
- následné vyčištění FAC a SCR,
- pokračování na další faktor (pokud existuje).

### Převod unary → bin (na OUT)
- převod unárního výsledku z ACC do binární podoby,
- zápis výsledku na OUT (MSB first),
- vyčištění pracovních pásek a zastavení ve stavu `ACCEPT_D`.

---

## 8. Spuštění projektu

### Struktura

```
src/
 ├── __init__.py
 ├── tm.py           # obecný vícepáskový TM engine
 └── product_bin.py  # konstrukce stroje + testy + demo
```

### Základní testy

```bash
python -m src.product_bin
```

### Krokový výpis (debug)

```bash
python -m src.product_bin --demo "#111#11#10##" --verbose
```

### Ořez okna kolem hlavy

```bash
python -m src.product_bin --demo "#111#11#10##" --verbose --window 40
```

### Export kódu stroje (encoding)

```bash
python -m src.product_bin --encode-file tm_code.txt
```

---

## 9. Ukázka konfigurace stroje

Příklad finální konfigurace (výsledek na pásce OUT):

```
[step=003409] state=ACCEPT_D

IN:  #######111#11#10#######
          ↑ (head=11)

ACC: #######L###############
          ↑ (head=1)

FAC: #######L###############
          ↑ (head=0)

SCR: #######L###############
          ↑ (head=7)

OUT: #######101010#########
          ↑ (head=1)
```

Interpretace:

- šipka `↑` označuje pozici hlavy,
- `(head=k)` je číselná pozice hlavy na dané pásce,
- výsledek je čitelný na pásce OUT (MSB first).

---

## 10. Ověření správnosti

Testovací případy:

| Vstup | Očekávaný výstup |
|---|---|
| `#101#11##` | `1111` |
| `#10#10##` | `100` |
| `#1#111##` | `111` |
| `#0#101##` | `0` |
| `#111#11#10##` | `101010` |
| `#1##` | `1` |

Stroj pro uvedené testy vždy:

- vypočítá korektní výsledek,
- zastaví v akceptačním stavu `ACCEPT_D`,
- zanechá výstupní pásku bez pomocných symbolů.

---

## 11. Zdroje

### Studijní materiály
- Zadání semestrální práce, prezentace a skripta (XTILO / 7TILO)  
  https://sites.google.com/view/7tilo-25/materiály

### Literatura
- Hopcroft, Motwani, Ullman – *Introduction to Automata Theory, Languages, and Computation*
- Sipser, M. – *Introduction to the Theory of Computation*

### Další zdroje / reference
- Wikipedia – *Turing machine*, *Multi-tape Turing machine*
- Open‑source simulátory a implementace vícepáskových Turingových strojů
- Konzultační a návrhové diskuse (včetně asistence AI nástrojů)

---

