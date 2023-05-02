import chess
import chess.polyglot
from chess import WHITE, KING, PAWN

from const import *

def is_mate_score(score):
	return abs(score) + 1000 >= CHECKMATE

def is_quiet_move(board, move, quiescence_depth=0):
	if board.is_capture(move):
		return False
	
	if board.is_check():
		return False
	
	if board.gives_check(move) and quiescence_depth <= QUIESCENCE_CHECK_DEPTH_LIMIT:
		return False
	
	if board.piece_at(move.from_square).piece_type == PAWN:
		if chess.square_rank(move.to_square) >= 6 and chess.square_rank(move.from_square) < chess.square_rank(move.to_square):
			return False
		if chess.square_rank(move.to_square) <= 1 and chess.square_rank(move.from_square) > chess.square_rank(move.to_square):
			return False

	if move.promotion is not None:
		return False

	return True

def lerp(start, end, position): # linear interpolation between start and end
	return int((1-position) * start + position * end)

def generate_pv_line(board, table):
	nboard = board.copy()
	
	pv = []

	zh = chess.polyglot.zobrist_hash(nboard)

	while zh in table:
		if table[zh][BEST_MOVE] is not None:
			pv.append(table[zh][BEST_MOVE])
			nboard.push(table[zh][BEST_MOVE])
			zh = chess.polyglot.zobrist_hash(nboard)
		else:
			break
	
	return pv
