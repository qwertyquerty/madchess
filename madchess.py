import chess
import chess.polyglot
from chess import WHITE, BLACK, KING, PAWN

import math

import threading

import time

from functools import partial
print = partial(print, flush=True)

VERSION = "MADCHESS v1.0"
AUTHOR = "Madeline"

UPPER = 1
LOWER = 2
EXACT = 3
CHECKMATE = 10_000

MAX_PTABLE_SIZE = 1_000_000

PIECE_VALUES = (0, 1, 3, 3, 5, 9, 0)
CP_PIECE_VALUES = (0, 100, 300, 300, 500, 900, 0)
ENDGAME_PIECE_COUNT = 16

STARTING_DEPTH = 1

QUIESCENCE_CHECK_DEPTH_LIMIT = 3 # stop looking for checks in quiescence after this quiescence depth limit

ASPIRATION_WINDOW_DEFAULT = CP_PIECE_VALUES[PAWN] // 4
ASPIRATION_INCREASE_EXPONENT = 4

MIDGAME_PIECE_POSITION_TABLES = (
	(None,),	
	( # Pawn
		0,  0,  0,  0,  0,  0,  0,  0,
		5, 10, 10,-20,-20, 10, 10,  5,
		5, -5,-10,  0,  0,-10, -5,  5,
		0,  0,  0, 20, 20,  0,  0,  0,
		5,  5, 10, 25, 25, 10,  5,  5,
		10, 10, 20, 30, 30, 20, 10, 10,
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

ENDGAME_PIECE_POSITION_TABLES = (
	(None,),	
	( # Pawn
		0,  0,  0,  0,  0,  0,  0,  0,
		5, 10, 10,-20,-20, 10, 10,  5,
		5, -5,-10,  0,  0,-10, -5,  5,
		0,  0,  0, 20, 20,  0,  0,  0,
		50, 50, 50, 50, 50, 50, 50, 50,
		100, 100, 100,100,100,100,100,100,
		300,300,300,300,300,300,300,300,
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

COLOR_MOD = (-1, 1)

MOVE_VALUE_CHECK = 500
MOVE_VALUE_ATTACK_LAST_MOVE = 100

def score_move(board, move):
	score = 0

	if len(board.move_stack) and move.to_square == board.move_stack[-1].to_square:
		# a simple, but quite efficient heuristic is capturing the last moved piece
		score += MOVE_VALUE_ATTACK_LAST_MOVE

	attacker = board.piece_at(move.from_square)
	victim = board.piece_at(move.to_square)

	if victim is not None:
		# MVV LVA
		score += CP_PIECE_VALUES[victim.piece_type] - CP_PIECE_VALUES[attacker.piece_type]
	
	# Change in positional scoring
	score -= MIDGAME_PIECE_POSITION_TABLES[attacker.piece_type][move.from_square if board.turn else chess.square_mirror(move.from_square)]
	score += MIDGAME_PIECE_POSITION_TABLES[attacker.piece_type][move.to_square if board.turn else chess.square_mirror(move.to_square)]

	# Promotions
	if move.promotion:
		score += CP_PIECE_VALUES[move.promotion]
	
	if board.gives_check(move):
		score += MOVE_VALUE_CHECK

	return score


def sorted_moves(moves, board):
	moves = list(moves)
	moves.sort(key=lambda move: score_move(board, move), reverse=True)
	return moves


def score_board(board, current_depth):
	if board.is_checkmate():
		return -CHECKMATE + current_depth
	
	if board.is_fivefold_repetition() or board.is_insufficient_material() or board.is_stalemate():
		return 0

	score = 0

	endgame = len(board.piece_map()) <= ENDGAME_PIECE_COUNT

	for square in range(64):
		pc = board.color_at(square)

		if pc is not None:
			pt = board.piece_type_at(square)

			if endgame:
				score += ENDGAME_PIECE_POSITION_TABLES[pt][square if pc == WHITE else chess.square_mirror(square)] * COLOR_MOD[pc]
			else:
				score += MIDGAME_PIECE_POSITION_TABLES[pt][square if pc == WHITE else chess.square_mirror(square)] * COLOR_MOD[pc]
			
			score += CP_PIECE_VALUES[pt] * COLOR_MOD[pc]

	score += len(list(board.legal_moves)) * COLOR_MOD[board.turn]

	return score if board.turn else -score


nodes = 0
pt_hits = 0
search_start_time = 0

position_table = {}

stop = False
lock = threading.Lock()

def alpha_beta(board, current_depth, max_depth, alpha, beta):
	if stop:
		return None, None
	
	global nodes
	nodes += 1

	alpha_orig = alpha

	pt_hash = chess.polyglot.zobrist_hash(board)
	pt_entry = position_table.get(pt_hash)
	
	if pt_entry is not None and (pt_entry["leaf_distance"]) == (max_depth-current_depth):
		if pt_entry["flag"] == EXACT:
			return pt_entry["value"], board if len(board.move_stack) >= len(pt_entry["board"].move_stack) else pt_entry["board"]
		elif pt_entry["flag"] == LOWER:
			alpha = max(alpha, pt_entry["value"])
		elif pt_entry["flag"]  == UPPER:
			beta = min(beta, pt_entry["value"])
		
		if alpha >= beta:
			return pt_entry["value"], board if len(board.move_stack) >= len(pt_entry["board"].move_stack) else pt_entry["board"]

	if current_depth == max_depth or board.is_game_over() or board.is_fivefold_repetition():
		return quiescence(board, current_depth + 1, max_depth, alpha, beta)

	best_board = board.copy()

	for move in sorted_moves(board.legal_moves, board):
		nboard = board.copy()
		nboard.push(move)

		score, end_board = alpha_beta(nboard, current_depth + 1, max_depth, -beta, -alpha)

		if score is None:
			return None, None

		score = -score

		if score > alpha:
			alpha = score
			best_board = end_board

		if alpha >= beta:
			break

	if pt_entry is not None or len(position_table) < MAX_PTABLE_SIZE:
		if pt_entry is None or (pt_entry["leaf_distance"]) > (max_depth-current_depth):
			flag = (UPPER if alpha <= alpha_orig else (LOWER if alpha >= beta else EXACT)) 
			position_table[pt_hash] = {"leaf_distance": max_depth-current_depth, "flag": flag, "value": alpha, "board": best_board}

	return alpha, best_board


def quiescence(board, current_depth, max_depth, alpha, beta):
	global nodes
	nodes += 1

	score = score_board(board, current_depth)

	if score >= beta:
		return beta, board

	alpha = max(alpha, score)

	best_board = board

	sorted_quiesence_moves = sorted_moves(
		(move for move in board.legal_moves if board.is_capture(move) or move.promotion is not None or board.is_check() or (board.gives_check(move) and (current_depth-max_depth) <= QUIESCENCE_CHECK_DEPTH_LIMIT)),
		board
	)

	for move in sorted_quiesence_moves:
		nboard = board.copy()
		nboard.push(move)

		score, end_board = quiescence(nboard, current_depth+1, max_depth, -beta, -alpha)
		score = -score

		if score >= beta:
			return beta, end_board
		
		if score > alpha:
			alpha = score
			best_board = end_board

	return alpha, best_board


def info_loop():
	global search_start_time
	search_start_time = time.time()
	start = search_start_time
	offset = 0
	while not stop:
		time.sleep(0.5)
		end = time.time()
		nps = (nodes-offset) / (end - start)
		offset = nodes
		start = time.time()

		with lock:
			print(f"info nodes {nodes} nps {int(nps)} time {int((time.time()-search_start_time) * 1000)} hashfull {int(len(position_table) / MAX_PTABLE_SIZE * 1000)}")


def iterative_deepening(board):
	global stop
	global nodes
	stop = False
	nodes = 0
	depth = STARTING_DEPTH
	position_table.clear()

	gamma = 0

	# Iterative deepening
	while not stop:
		aspw_lower = -ASPIRATION_WINDOW_DEFAULT
		aspw_higher = ASPIRATION_WINDOW_DEFAULT

		while True:
			alpha = gamma + aspw_lower
			beta = gamma + aspw_higher

			score, end_board = alpha_beta(board, 0, depth, alpha, beta)

			if score <= alpha:
				aspw_lower *= ASPIRATION_INCREASE_EXPONENT
			elif score >= beta:
				aspw_higher *= ASPIRATION_INCREASE_EXPONENT
			else:
				break

		with lock:
			depth_string = f"depth {depth} seldepth {len(end_board.move_stack) - len(board.move_stack)}" # full search depth / quiescence search depth
			time_string = f"time {int((time.time()-search_start_time) * 1000)}" # time spent searching this position
			hashfull_string = f"hashfull {int(len(position_table) / MAX_PTABLE_SIZE * 1000)}" # how full the transposition table is
			pv_string = f"pv {' '.join([str(move) for move in end_board.move_stack[len(board.move_stack):]])}" # move preview

			if end_board.is_checkmate(): # Checkmate is found, report how many moves its in
				mate_in = (len(end_board.move_stack) - len(board.move_stack)) * COLOR_MOD[score > 0]
				print(f"info nodes {nodes} {time_string} {hashfull_string} {depth_string} score mate {mate_in} {pv_string}")
			else:
				print(f"info nodes {nodes} {time_string} {hashfull_string} {depth_string} score cp {score} {pv_string}")
		
		# Once a mate is found, it wont do us any better to try to find it again in more moves
		if end_board.is_checkmate():
			break

		gamma = score
		depth += 1

stop = True

board = chess.Board()

search_thread = None
node_info_thread = None

while True:
	line = input()
	args = line.split()
	cmd = args[0] if len(args) else None

	if cmd == "uci":
		print(f"id name {VERSION}")
		print(f"id author {AUTHOR}")
		print("uciok")
	
	elif cmd == "isready":
		print("readyok")
	
	elif cmd == "quit":
		stop = True
		break

	elif cmd == "position":
		if "fen" in args:
			fen = line.split(" fen ")[1].split("moves")[0]
			board = chess.Board(fen=fen)
		elif "startpos" in args:
			board = chess.Board()
			
		if "moves" in args:
			moves = line.split(" moves ")[1].split()
			for move in moves:
				board.push(chess.Move.from_uci(move))
			
	elif cmd == "go":
		if stop:
			search_thread = threading.Thread(target=lambda: iterative_deepening(board), daemon=True)
			node_info_thread = threading.Thread(target=lambda: info_loop(), daemon=True)
			search_thread.start()
			node_info_thread.start()

	elif cmd == "stop":
		stop = True
		while search_thread.is_alive() or node_info_thread.is_alive():
			pass
