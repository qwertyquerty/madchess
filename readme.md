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
- [x] UCI compliant
    - [x] plays on time
- [x] board evaluation
    - [x] piece specific positions
    - [x] game phase tapering
    - [x] mobility
    - [x] will to push
    - [x] pawn structure
        - [x] isolated pawns
        - [x] doubled/tripled pawns
        - [ ] passed pawns
        - [ ] pawn chains
    - [x] doubled bishops
    - [x] material value
- [x] minimax search
- [x] quiescence search
    - [x] delta pruning
- [x] iterative deepening
- [x] transposition tables
- [x] pruning
    - [x] alpha beta pruning
        - [x] move ordering
            - [x] MVV LVA
            - [x] positional changes
            - [x] best move from transposition table
            - [x] retake last moved
            - [x] killer move heuristic
            - [x] countermove heuristic
            - [x] history heuristic
            - [ ] static exchange evaluation
    - [x] aspiration windows with gamma
    - [x] null window
    - [x] futility pruning
    - [x] reverse futility pruning
    - [x] principal variance search
    - [x] late move reductions
    - [x] null move reduction
    - [ ] scout search or MTD(f)
    - [ ] razoring
- [ ] parallel processing
- [ ] selective searching
