import chess
from chess import WHITE, BLACK, KING, PAWN

from collections import namedtuple, defaultdict
import threading

import time

from functools import partial
print = partial(print, flush=True)

VERSION = "MADCHESS v1.0"
AUTHOR = "Madeline"

MAX_DEPTH = 100

MAX_QUIESCENCE = 10
QS = 15

PIECE_VALUES = (0, 1, 3, 3, 5, 9, 0)
CP_PIECE_VALUES = (0, 100, 300, 300, 500, 900, 0)

CHECKMATE = 10000

PIECE_POSITION_TABLES = (
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

COLOR_MOD = (-1, 1)


def score_board(board):
	if board.is_checkmate():
		return 10000 if board.turn else -10000
	
	if board.is_fivefold_repetition() or board.is_insufficient_material() or board.is_stalemate():
		return 0

	score = 0

	for square in range(64):
		pc = board.color_at(square)

		if pc is not None:
			pt = board.piece_type_at(square)

			score += (
				(
					PIECE_POSITION_TABLES[pt][square if pc == WHITE else chess.square_mirror(square)]
					if pc else
					-PIECE_POSITION_TABLES[pt][square if pc == WHITE else chess.square_mirror(square)]
				)
				+ CP_PIECE_VALUES[pt] if pc else -CP_PIECE_VALUES[pt]
			)

	return score * COLOR_MOD[board.turn]


nodes = 0
stop = False
lock = threading.Lock()

def alpha_beta(board, current_depth, max_depth, alpha, beta):
	if stop:
		return None, None
	
	global nodes
	nodes += 1

	if current_depth == max_depth or board.is_game_over():
		value, end_board = quiescence(board, current_depth, max_depth, alpha, beta)
		return value, end_board

	best_board = board

	for move in board.legal_moves:
		nboard = board.copy()
		nboard.push(move)

		value, end_board = alpha_beta(nboard, current_depth + 1, max_depth, -beta, -alpha)

		if value is None:
			return None, None

		value = -value

		if value >= beta:
			return beta, end_board
		
		if value > alpha:
			alpha = value
			best_board = end_board
		
		if alpha >= beta:
			break

	return alpha, best_board


def quiescence(board, current_depth, max_depth, alpha, beta):
	global nodes
	nodes += 1

	score = score_board(board)

	if score >= beta:
		return beta, board

	alpha = max(alpha, score)

	if (current_depth-max_depth) >= max_depth or board.is_game_over():
		return score, board

	best_board = board

	for move in board.legal_moves:
		if board.is_capture(move) or board.gives_check(move) or board.is_check():
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

def nodes_info_loop():
	start = time.time()
	while not stop:
		time.sleep(0.25)
		end = time.time()
		nps = nodes / (end - start)
		with lock:
			print(f"info nodes {nodes} nps {int(nps)}")

def begin(board):
	global stop
	global nodes
	stop = False
	
	nodes = 0
	base_board = board.copy()

	for depth in range(1, MAX_DEPTH):
		value, end_board = alpha_beta(board, 0, depth, -CHECKMATE, CHECKMATE)

		if stop == True:
			break
		
		with lock:
			print(f"info depth {depth} score cp {value} pv {' '.join([str(move) for move in end_board.move_stack[len(base_board.move_stack):]])} nodes {nodes}")

def halt():
	global stop
	stop = True

board = chess.Board()

search_thread = threading.Thread(target=lambda: begin(board), daemon=True)
node_info_thread = threading.Thread(target=lambda: nodes_info_loop(), daemon=True)

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
		search_thread = threading.Thread(target=lambda: begin(board), daemon=True)
		node_info_thread = threading.Thread(target=lambda: nodes_info_loop(), daemon=True)
		search_thread.start()
		node_info_thread.start()

	elif cmd == "stop":
		halt()
		while search_thread.is_alive() or node_info_thread.is_alive():
			pass
