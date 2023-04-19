# QChess

Simple Alpha Beta UCI Compliant Chess Engine in Python

***Running this engine with pypy is heavily recommended***

### Installation

`pip3 install -r requirements.txt`

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
- [x] aspiration windows with gamma
- [ ] null window
- [ ] futility pruning
- [ ] better quiescence
- [ ] scout search or MTD(f)
- [ ] parallel processing
- [ ] draw claims in eval function
- [ ] more in depth selectivity searching
- [ ] fully UCI compliant
