import chess
from chess import WHITE, KING, PAWN

from const import *

def is_mate_score(score):
	return abs(score) >= (CHECKMATE - 1000)

def is_quiet_move(board, move, quiescence_depth=0):
	if board.is_capture(move):
		return False
	
	if move.promotion is not None:
		return False
	
	if board.is_check():
		return False
	
	if (board.gives_check(move) and quiescence_depth <= QUIESCENCE_CHECK_DEPTH_LIMIT):
		return False
	
	if board.piece_at(move.from_square).piece_type == PAWN:
		if chess.square_rank(move.to_square) >= 6 and chess.square_rank(move.from_square) < chess.square_rank(move.to_square):
			return False
		if chess.square_rank(move.to_square) <= 1 and chess.square_rank(move.from_square) > chess.square_rank(move.to_square):
			return False
	
	return True

def lerp(start, end, position): # linear interpolation between start and end
	return (1-position) * start + position * end

def clear_pv_table(table):
	for i in range(PV_SIZE):
		table[i] = [None for i in range(PV_SIZE)]

def update_pv_table(table, move, depth, leaf):
	if depth < PV_SIZE:
		table[depth][depth] = move
	
	for i in range(depth+1, PV_SIZE):
		lower_move = table[depth+1][i]
		if lower_move is None: break
		table[depth][i] = lower_move

	if leaf:
		for i in range(depth+1, PV_SIZE):
			if table[depth][i] is None: break
			table[depth][i] = None

def generate_pv_line(table):
	pv = []
	for i in range(PV_SIZE):
		move = table[0][i]
		if move is None: break
		pv.append(move)
	
	return pv
