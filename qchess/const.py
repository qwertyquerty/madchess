from chess import WHITE, KING, PAWN

import math

### Configuration ###

## Metadata ##
VERSION = "QChess v2.0"
AUTHOR = "qwertyquerty"

## Enums ##
UPPER = 1
LOWER = 2
EXACT = 3

# Used to multiply ratings based on whos turn it is
COLOR_MOD = (-1, 1)

# Maximum depth we will ever search
MAX_DEPTH = 1000

# Evaluation score for a white checkmate, basically +100.0
CHECKMATE = 100_000

## Transposition tables ##
# Maximum amount of entries in the positional transposition table
MAX_PTABLE_SIZE = 1_000_000

## Piece Values (-, p, n, b, r, q, k) ##
PIECE_VALUES = (0, 1, 3, 3, 5, 9, 0) # pawns
CP_PIECE_VALUES = (0, 100, 300, 300, 500, 900, 0) # centipawns

# More accurate centipawn piece values based on game phase
CP_PIECE_VALUES_MIDGAME = (0, 85, 325, 330, 444, 998, 0)
CP_PIECE_VALUES_ENDGAME = (0, 80, 289, 318, 560, 1016, 0)

# Slight bonus for the player to move
TEMPO_BONUS = 20 # cp

# Having both bishops is mildly good
DOUBLE_BISHOP_BONUS = 30 # cp

# Doubled / tripled pawns are bad
DOUBLED_PAWN_PENALTY = -15 # cp
TRIPLED_PAWN_PENALTY = -30 # cp

# If there are <= to this many pieces on the board, we are in endgame
ENDGAME_PIECE_COUNT = 16

# First depth to search in iterative deepening
STARTING_DEPTH = 1

# Stop looking for checks in quiescence after this quiescence depth limit
QUIESCENCE_CHECK_DEPTH_LIMIT = 3

## Aspiration Windows ##
# How big (+/-) the aspiration window is around gamma
ASPIRATION_WINDOW_DEFAULT = CP_PIECE_VALUES[PAWN] // 4
# If the real value is outside of the aspiration window, multiply the limiting bound by this
ASPIRATION_INCREASE_EXPONENT = 4

## Futility Pruning ##
FUTILITY_MARGINS = (0, 100, 200, 300, 400, 500)
FUTILITY_DEPTH = 5

## Reverse Futility Pruning
REVERSE_FUTILTIY_MARGINS = (0, 70, 150, 240, 340, 450, 580, 720)
REVERSE_FUILITY_DEPTH = 7

## Late move reduction
LATE_MOVE_REDUCTION_MOVES = 4
LATE_MOVE_REDUCTION_LEAF_DISTANCE = 3
LATE_MOVE_REDUCTION_TABLE_SIZE = 32
LATE_MOVE_REDUCTION_TABLE = [[int(0.25 * math.log(i) * math.log(j) + 0.7) for j in range(1, LATE_MOVE_REDUCTION_TABLE_SIZE+1)] for i in range(1, LATE_MOVE_REDUCTION_TABLE_SIZE+1)]

## Positional values ##
# Ratings for piece positionally in midgame, (first rank is on top)
MIDGAME_PIECE_POSITION_TABLES = (
	(None,),	
	( # Pawn
		 0,  0,  0,  0,  0,  0,  0,  0,
		 5, 10, 10,-20,-20, 10, 10,  5,
		 5, -5,-10,  0,  0,-10, -5,  5,
		 5,  5,  0, 20, 20,  0,  5,  5,
		10, 10, 10, 25, 25, 10, 10, 10,
		10, 15, 20, 30, 30, 20, 15, 10,
		50, 50, 50, 50, 50, 50, 50, 50,
	     0,  0,  0,  0,  0,  0,  0,  0,
	),

	( # Knight
		-50,-40,-30,-30,-30,-30,-40,-50,
		-40,-20,  0,  5,  5,  0,-20,-40,
		-30,  5, 10, 15, 15, 10,  5,-30,
		-30,  0, 15, 20, 20, 15,  0,-30,
		-30,  5, 15, 20, 20, 15,  5,-30,
		-30,  0, 10, 15, 15, 10,  0,-30,
		-40,-20,  0,  0,  0,  0,-20,-40,
		-50,-40,-30,-30,-30,-30,-40,-50,
	),

	( # Bishop
		-20,-10,-10,-10,-10,-10,-10,-20,
		-10,  5,  0,  0,  0,  0,  5,-10,
		-10, 10, 10, 10, 10, 10, 10,-10,
		-10,  0, 10, 10, 10, 10,  0,-10,
		-10,  5,  5, 10, 10,  5,  5,-10,
		-10,  0,  5, 10, 10,  5,  0,-10,
		-10,  0,  0,  0,  0,  0,  0,-10,
		-20,-10,-10,-10,-10,-10,-10,-20,
	),

	( # Rook
		0,  0,  0,  5,  5,  0,  0,  0,
		0,  0,  0,  0,  0,  0,  0,  0,
		0,  0,  0,  0,  0,  0,  0,  0,
		0,  0,  0,  0,  0,  0,  0,  0,
		0,  0,  0,  0,  0,  0,  0,  0,
		0,  0,  0,  0,  0,  0,  0,  0,
		5, 10, 10, 10, 10, 10, 10,  5,
		0,  0,  0,  0,  0,  0,  0,  0
	),

	( # Queen
		-20,-10,-10, -5, -5,-10,-10,-20,
		-10,  0,  5,  0,  0,  0,  0,-10,
		-10,  5,  5,  5,  5,  5,  0,-10,
		  0,  0,  5,  5,  5,  5,  0, -5,
		 -5,  0,  5,  5,  5,  5,  0, -5,
		-10,  0,  5,  5,  5,  5,  0,-10,
		-10,  0,  0,  0,  0,  0,  0,-10,
		-20,-10,-10, -5, -5,-10,-10,-20
	),

	( # King
		 20, 30, 10,  0,  0, 10, 30, 20,
		 20, 20,  0,  0,  0,  0, 20, 20,
		-10,-20,-20,-20,-20,-20,-20,-10,
		-20,-30,-30,-40,-40,-30,-30,-20,
		-30,-40,-40,-50,-50,-40,-40,-30,
		-30,-40,-40,-50,-50,-40,-40,-30,
		-30,-40,-40,-50,-50,-40,-40,-30,
		-30,-40,-40,-50,-50,-40,-40,-30
	)
)

# Ratings for piece positionally in endgame, (first rank is on top)
ENDGAME_PIECE_POSITION_TABLES = (
	(None,),	
	( # Pawn, we want to try and promote during endgame
		  0,  0,  0,  0,  0,  0,  0,  0,
		  5, 10, 10,-20,-20, 10, 10,  5,
		  5, -5,-10,  0,  0,-10, -5,  5,
		  0,  0,  0, 20, 20,  0,  0,  0,
		 50, 50, 50, 50, 50, 50, 50, 50,
		100,100,100,100,100,100,100,100,
		200,200,200,200,200,200,200,200,
		  0,  0,  0,  0,  0,  0,  0,  0,
	),

	( # Knight
		-50,-40,-30,-30,-30,-30,-40,-50,
		-40,-20,  0,  5,  5,  0,-20,-40,
		-30,  5, 10, 15, 15, 10,  5,-30,
		-30,  0, 15, 20, 20, 15,  0,-30,
		-30,  5, 15, 20, 20, 15,  5,-30,
		-30,  0, 10, 15, 15, 10,  0,-30,
		-40,-20,  0,  0,  0,  0,-20,-40,
		-50,-40,-30,-30,-30,-30,-40,-50,
	),

	( # Bishop
		-20,-10,-10,-10,-10,-10,-10,-20,
		-10,  5,  0,  0,  0,  0,  5,-10,
		-10, 10, 10, 10, 10, 10, 10,-10,
		-10,  0, 10, 10, 10, 10,  0,-10,
		-10,  5,  5, 10, 10,  5,  5,-10,
		-10,  0,  5, 10, 10,  5,  0,-10,
		-10,  0,  0,  0,  0,  0,  0,-10,
		-20,-10,-10,-10,-10,-10,-10,-20,
	),

	( # Rook
		0,  0,  0,  5,  5,  0,  0,  0,
		0,  0,  0,  0,  0,  0,  0,  0,
		0,  0,  0,  0,  0,  0,  0,  0,
		0,  0,  0,  0,  0,  0,  0,  0,
		0,  0,  0,  0,  0,  0,  0,  0,
		0,  0,  0,  0,  0,  0,  0,  0,
		5, 10, 10, 10, 10, 10, 10,  5,
		0,  0,  0,  0,  0,  0,  0,  0
	),

	( # Queen
		-20,-10,-10, -5, -5,-10,-10,-20,
		-10,  0,  5,  0,  0,  0,  0,-10,
		-10,  5,  5,  5,  5,  5,  0,-10,
		  0,  0,  5,  5,  5,  5,  0, -5,
		 -5,  0,  5,  5,  5,  5,  0, -5,
		-10,  0,  5,  5,  5,  5,  0,-10,
		-10,  0,  0,  0,  0,  0,  0,-10,
		-20,-10,-10, -5, -5,-10,-10,-20
	),

	( # King, move to center in endgame
		-50,-30,-30,-30,-30,-30,-30,-50,
		-30,-30,  0,  0,  0,  0,-30,-30,
		-30,-10, 20, 30, 30, 20,-10,-30,
		-30,-10, 30, 40, 40, 30,-10,-30,
		-30,-10, 30, 40, 40, 30,-10,-30,
		-30,-10, 20, 30, 30, 20,-10,-30,
		-30,-20,-10,  0,  0,-10,-20,-30,
		-50,-40,-30,-20,-20,-30,-40,-50
	)
)


WILL_TO_PUSH = (
	 0,  0,  0,  0,  0,  0,  0,  0,
	10, 10, 10, 10, 10, 10, 10, 10,
	10, 10, 10, 10, 10, 10, 10, 10,
	20, 20, 20, 20, 20, 20, 20, 20,
	20, 20, 20, 20, 20, 20, 20, 20,
	30, 30, 30, 30, 30, 30, 30, 30,
	30, 30, 30, 30, 30, 30, 30, 30,
	30, 30, 30, 30, 30, 30, 30, 30
)
