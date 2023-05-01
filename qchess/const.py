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

MIDGAME = 0
ENDGAME = 1

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
PHASED_CP_PIECE_VALUES = (
    (0, 85, 325, 330, 444, 998, 0), # midgame
    (0, 80, 289, 318, 560, 1016, 0) # endgame
)

# Slight bonus for the player to move
TEMPO_BONUS = (20, 0) # midgame, endgame

# Having both bishops is mildly good
DOUBLE_BISHOP_BONUS = (34, 55) # cp

# Doubled / tripled pawns are bad
DOUBLED_PAWN_PENALTY = (-7, -20) # cp
TRIPLED_PAWN_PENALTY = (-12, -37) # cp
ISOLATED_PAWN_PENALTY = (-7, -20)

# First depth to search in iterative deepening
STARTING_DEPTH = 1

# Stop looking for checks in quiescence after this quiescence depth limit
QUIESCENCE_CHECK_DEPTH_LIMIT = 3

## Aspiration Windows ##
# How big (+/-) the aspiration window is around gamma
ASPIRATION_WINDOW_DEFAULT = CP_PIECE_VALUES[PAWN]
# If the real value is outside of the aspiration window, multiply the limiting bound by this
ASPIRATION_INCREASE_EXPONENT = 4
# Only use aspiration windows at this depth or greater
ASPIRATION_WINDOW_DEPTH = 5

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
    # Pawn	
	(0, 0, 0, 0, 0, 0, 0, 0, -19, -18, -15, -20, -6, 16, 27, -7, -19, -15, -9, -12, -2, 2, 23, 4, -24, -18, -9, 8, 3, 8, 4, -10, -16, -12, -2, 5, 27, 24, 19, 4, 18, 11, 31, 46, 51, 77, 56, 32, 96, 105, 72, 106, 65, 68, -21, -21, 0, 0, 0, 0, 0, 0, 0, 0),
	# Knight
	(-80, -40, -33, -27, -20, -19, -43, -52, -45, -35, -22, -10, -10, -1, -21, -20, -36, -17, 0, 13, 21, 2, 0, -24, -23, -8, 11, 16, 23, 15, 16, -9, -5, -1, 24, 50, 24, 52, 8, 19, -15, 29, 59, 70, 75, 70, 50, -7, -51, 1, 29, 31, 25, 60, 31, 20, -110, -100, -39, -32, -26, -80, -80, -110),
	# Bishop
	(-8, 14, -7, -2, -3, -12, 18, 0, 2, 5, 16, -8, 5, 14, 17, 1, -2, 4, 7, 7, 10, 8, 5, 10, -18, -15, -4, 26, 17, 0, 0, 2, -13, 0, 16, 34, 27, 26, 4, -4, -10, 19, 26, 21, 15, 45, 49, 21, -21, 16, 2, -7, 16, 9, 20, -5, -4, -70, -9, -70, -70, -70, -46, -43),
	# Rook
	(-16, -13, -6, 7, 6, 5, 4, -17, -35, -18, -17, -13, -11, 2, 9, -22, -25, -25, -23, -17, -8, -15, 9, -3, -28, -26, -11, -15, -8, -24, -10, -21, -21, 3, -10, 2, 1, 8, 8, 2, -6, 14, 11, 4, 31, 33, 64, 34, -9, 1, 4, 15, -1, 36, 24, 16, -18, -4, 13, -13, -5, 6, 32, 28),
	# Queen
	(-2, -7, 0, 6, 4, -3, -5, -6, -7, -4, 6, 11, 10, 18, 6, 26, -12, -5, -1, -6, -6, 2, 0, -3, -12, -10, -13, -12, -12, -9, 0, -4, -18, -6, -11, -20, 1, 1, 4, 9, -1, -14, 0, -15, 12, 44, 60, 35, -17, -18, -3, -8, 9, 13, 11, 51, -34, -19, -8, -22, 3, 19, 45, 8),
	# King
	(33, 59, 32, -40, 6, -25, 42, 39, 51, 17, 4, -27, -27, -18, 20, 30, -18, 3, -27, -43, -31, -43, -16, -43, -23, -26, -41, -54, -67, -22, -28, -56, -13, -14, -34, -53, -49, -25, -12, -20, -36, 0, -30, -30, -23, 0, 0, 1, -37, -13, -42, -13, -26, -5, 0, 10, -51, -37, -29, -43, -34, -4, 0, -29)
)

# Ratings for piece positionally in endgame, (first rank is on top)
ENDGAME_PIECE_POSITION_TABLES = (
	(None,),
    # Pawn
	(0, 0, 0, 0, 0, 0, 0, 0, 17, 30, 19, 32, 31, 21, 14, 4, 12, 23, 12, 24, 23, 18, 14, 0, 23, 29, 13, 5, 7, 10, 16, 6, 49, 50, 31, 18, 12, 19, 35, 29, 115, 138, 110, 81, 67, 65, 114, 100, 178, 170, 179, 144, 154, 128, 186, 193, 0, 0, 0, 0, 0, 0, 0, 0),
	# Knight
	(-37, -22, -11, -1, -8, -17, -6, -21, -14, -4, 4, 6, 6, 0, -20, -11, -18, 1, 5, 18, 21, 4, -1, -15, 7, 12, 27, 20, 27, 17, 5, -4, -9, 14, 27, 24, 21, 19, 13, -3, 4, -1, 13, 10, 11, 1, -13, -14, -9, -6, -11, -4, -11, 2, -28, -19, -88, -38, -17, -23, -8, -26, -19, -89),
	# Bishop
	(-17, 0, 5, -9, -5, 10, -12, -22, -13, -11, -16, 4, -4, -3, -3, -10, -5, -7, 1, -2, 6, 2, 0, -14, -12, 3, 4, -3, 7, -4, -5, -32, -12, -6, 3, 4, -4, -1, -4, -13, -3, -8, -11, -12, -18, -12, -12, -10, -13, -11, -20, -9, -30, -20, -9, -25, -4, -2, -14, -9, -19, -16, -11, -18),
	# Rook
	(9, 7, 6, 4, -3, -1, -6, -3, 3, -1, 5, 3, -4, -12, -10, -8, 5, 6, 5, 2, -4, -12, -17, -19, 6, 8, 13, 14, 2, 1, 3, 2, 16, 8, 17, 12, -5, -6, 2, -6, 14, 11, 7, 12, -6, -4, 2, 1, 20, 21, 26, 12, 11, 9, 4, 16, 29, 11, 21, 20, 18, 16, 8, 12),
	# Queen
	(-11, -12, -16, 10, -5, -19, -22, -16, -15, -16, -12, -2, 3, -21, -19, -68, -3, 2, 7, 10, 25, 5, 12, 20, -5, -3, 5, 34, 31, 26, 7, 31, 14, 11, 10, 35, 27, 42, 33, 15, 6, 21, 34, 36, 34, 41, 0, 40, 16, 10, 34, 44, 56, 26, 19, 27, 15, -6, 17, 45, 21, 21, -3, 20),
	# King
	(-82, -60, -43, -33, -44, -32, -55, -86, -47, -23, -11, -2, 3, -2, -20, -40, -34, -11, 9, 24, 23, 18, -2, -17, -34, 2, 29, 43, 46, 30, 11, -7, -17, 15, 33, 42, 45, 43, 26, -4, -10, 10, 35, 40, 46, 53, 30, 2, -25, 4, 10, 16, 22, 27, 20, -7, -84, -46, -28, -6, -23, -11, 0, -90)
)

PIECE_MOBILITY_TABLES = (
    (None,),
    (None,), # pawn, unused
    ( # Knight
    	(-21, -6, 2, 5, 9, 11, 11, 11, 10),
        (-21, -6, 2, 5, 9, 11, 11, 11, 10)
	),
    ( # Bishop
		(-45, -34, -22, -16, -7, 3, 9, 13, 16, 14, 14, 16, 16, 8),
        (-45, -34, -22, -16, -7, 3, 9, 13, 16, 14, 14, 16, 16, 8)
	),
    ( # Rook
		(-29, -16, -12, -6, -4, 1, 4, 6, 9, 13, 13, 14, 16, 17, 17),
        (-29, -16, -12, -6, -4, 1, 4, 6, 9, 13, 13, 14, 16, 17, 17)
	),
    ( # Queen
    	(-55, -80, -39, -37, -44, -33, -14, -29, -13, -17, 2, -4, 2, 15, 20, 27, 22, 42, 47, 48, 51, 51, 54, 47, 50, 56, 46, 75),
        (-20, -11, -31, -21, -19, -14, -10, -9, -5, -2, -2, 0, 3, -1, 3, 4, 3, 2, 6, 16, 25, 25, 19, 33, 28, 37, 20, 78)
	),
    (None,), #king, unused
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
