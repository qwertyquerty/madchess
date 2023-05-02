# QChess

Simple Alpha Beta UCI Compliant Chess Engine in Python

*Currently the strongest Python Chess engine*

***Running this engine with pypy is heavily recommended***

### Installation

- **cpython**: `pip3 install -r requirements.txt`
- **pypy**: `pypy -m pip install -r requirements.txt`

### Usage

Load `qchess.bat` into any UCI compliant Chess program and set the working directory to your cloned repository folder

### Todo List

- [x] fully documented
- [x] alpha beta pruned minimax search
- [x] piece specific positional evaluation
- [x] quiescence search
- [x] iterative deepening
- [x] transposition tables
    - [x] positional / best move
- [x] move ordering
    - [x] MVV LVA
    - [x] positional changes
    - [x] best move from transposition table
    - [x] killer move heuristic
    - [x] countermove heuristic
    - [x] history heuristic
    - [ ] static exchange evaluation
- [x] aspiration windows with gamma
- [x] null window
- [x] futility pruning
- [x] reverse futility pruning
- [x] better quiescence
- [x] principal variance search
- [x] late move reductions
- [x] null move reduction
- [ ] scout search or MTD(f)
- [ ] parallel processing
- [x] draw claims in eval function
- [ ] more in depth selectivity searching
- [ ] fully UCI compliant
- [ ] razoring
